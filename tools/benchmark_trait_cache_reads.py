"""Compare cached Trait reads against a checkout using an isolated synthetic DB."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--charts', type=int, default=500)
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkout.resolve()))
    from ephemeraldaddy.core import db
    from ephemeraldaddy.analysis import trait_prediction_index as runtime
    with tempfile.TemporaryDirectory(prefix='trait-cache-benchmark-') as directory:
        db.DB_DIR = Path(directory)
        db.DB_PATH = db.DB_DIR / 'charts.db'
        traits = [{'uid': f't{i}', 'name': f'Trait{i}', 'profile': {'signs': {'Aries': i + 1}}} for i in range(30)]
        uids = [f'PERFUID{i:07d}' for i in range(args.charts)]
        conn = db._get_conn()
        with conn:
            conn.executemany('INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,0,0,?)', [(uid, uid, '2000-01-01T00:00:00+00:00', '2026-01-01') for uid in uids])
            conn.executemany('INSERT INTO chart_trait_likelihoods(chart_uid,trait_uid,trait_name,likelihood,trait_signature,chart_signature,updated_at) VALUES(?,?,?,80,?,?,?)', [(uid, trait['uid'], trait['name'], 'generation', 'astro', '2026-01-01') for uid in uids for trait in traits])
            conn.executemany('INSERT INTO trait_baseline_snapshots(norm_signature,trait_signature,trait_uid,trait_name,db_average,chart_count,norm_state,updated_at) VALUES(?,?,?,?,50,500,?,?)', [('norm', 'generation', trait['uid'], trait['name'], '{}', '2026-01-01') for trait in traits])
        conn.close()
        (db.DB_DIR / '.prediction_norms_source.json').write_text(json.dumps({'source': 'my_database'}), encoding='utf-8')
        (db.DB_DIR / '.prediction_norms_snapshot.json').write_text(json.dumps({'version': 1, 'snapshot_id': 'static', 'trait_baselines': {f"uid:{trait['uid']}": {'db_average': 50} for trait in traits}}), encoding='utf-8')
        def forbidden(*args, **kwargs):
            raise AssertionError('Cached lookup calculated a prediction')
        runtime.calculate_trait_likelihoods = forbidden
        original = db._get_conn
        selects = []
        def connect():
            connection = original()
            connection.set_trace_callback(lambda sql: selects.append(sql) if sql.lstrip().upper().startswith(('SELECT', 'WITH')) else None)
            return connection
        db._get_conn = connect
        index = runtime.TraitPredictionIndex()
        runs = []
        for _ in range(3):
            selects.clear()
            started = time.perf_counter()
            if hasattr(index, 'results_for_uids'):
                results = index.results_for_uids(uids, [traits[0]])
            else:
                results = {uid: index.read_cached(runtime.TraitPredictionQuery(uid, 'astro', 'generation', 'norm'), [traits[0]]) for uid in uids}
            assert all(result and result.likelihoods['Trait0'] == 80 for result in results.values())
            runs.append({'ms': round((time.perf_counter() - started) * 1000, 2), 'selects': len(selects)})
        print(json.dumps({'charts': len(uids), 'stored_traits': len(traits), 'requested_traits': 1, 'runs': runs, 'median_ms': statistics.median(run['ms'] for run in runs)}))


if __name__ == '__main__':
    main()
