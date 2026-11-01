"""Synthetic safeguards for nested selection and the comparative checkpoint loop."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from motor_v2.comparison import bucket, choose_options, experiment, run, scope_pool
from motor_v2.runner import read


def panel():
    return [dict(dist=d, year=y, group=str(m), feature_year=y-1,
                 feature_available=f'{y-1}-12-31', feature_revision_available=f'{y-1}-12-31',
                 target_available=f'{y}-12-31', x=[3., .5, 1.], stock=20., y=21.,
                 rupture=False, key=f'{d}:{y}:{m}')
            for d in (26, 6585, 6600) for y in (2023, 2024, 2025) for m in range(60)]


class ComparativeTests(unittest.TestCase):
    def cfg(self, output):
        return dict(output=str(output), comparison_input='synthetic', dists=[26,6585,6600],
                    threads=1, models=['ridge'], origins=[2023,2024], max_trials=2,
                    seed=42, territorial_folds=3, seconds_per_candidate=30, min_independent_origins=3)

    def test_shared_is_three_company_pool_with_cross_company_group_exclusion(self):
        train, peers = scope_pool(panel(), 26, 2024, 'point_in_time', 'shared_pilot', {'3','4'})
        self.assertEqual(set(peers), {26,6585,6600})
        self.assertFalse({'3','4'} & {r['group'] for r in train})
        self.assertTrue(all(r['year']<=2024 for r in train))

    def test_future_inner_labels_cannot_select_features_or_parameters(self):
        rows=panel()
        for r in rows:
            if r['year']==2024:r['target_available']='2025-01-01'
        with patch('motor_v2.comparison.fit_predict', side_effect=ValueError('no validation labels')) as fit:
            _, trials, reason=choose_options(rows,26,2024,'point_in_time','shared_pilot',set(),'ridge',self.cfg('.'))
        self.assertTrue(all(not call.args[3] for call in fit.call_args_list))
        self.assertTrue(all(t['mae'] is None for t in trials))
        self.assertIn('no_eligible_inner_fold', reason)

    def test_peer_similarity_does_not_impute_unknown_urbanization(self):
        rows=panel()
        for r in rows:
            if r['dist']==26:r['x'][1]=None
        train,peers=scope_pool(rows,26,2024,'point_in_time','peers_pilot',set())
        self.assertEqual(train,[]);self.assertEqual(peers,[])

    def test_nested_selection_never_sees_outer_territories_or_future_training(self):
        rows=panel();heldout={r['group'] for r in rows if bucket(r['group'],3)==0}
        observed=[]
        def fit(model,opt,train,test,seed):
            observed.append((train,test))
            self.assertTrue(train and test)
            self.assertLess(max(r['year'] for r in train), min(r['year'] for r in test))
            self.assertFalse({r['group'] for r in train}&{r['group'] for r in test})
            self.assertFalse(heldout & {r['group'] for r in train+test})
            return [r['stock'] for r in test], {}
        with patch('motor_v2.comparison.fit_predict',side_effect=fit):
            _,_,reason=choose_options(rows,26,2024,'point_in_time','shared_pilot',heldout,'ridge',self.cfg('.'))
        self.assertEqual(reason,'inner_holdout_selection');self.assertEqual(len(observed),4)  # every eligible feature subset is mandatory: [0],[0,2],[0,1],[0,1,2]

    def test_comparison_stop_resume_reuse_and_corrupt_checkpoint(self):
        with tempfile.TemporaryDirectory(dir='D:/NUCLEO_BDGD_2025/motor_v2',prefix='comparison-test-') as tmp:
            cfg=self.cfg(tmp);stop=Path(tmp)/'STOP';calls=[]
            def calculate(*args):
                calls.append(1)
                if len(calls)==2:stop.write_text('test')
                return dict(predictions=[],folds=[],failures=[dict(reason='synthetic test only')])
            with patch('motor_v2.comparison.load_panel',return_value=(panel(),[],{'synthetic':'test'})), patch('motor_v2.comparison.investigate',return_value={}), patch('motor_v2.comparison.experiment',side_effect=calculate):
                out=run(cfg,stop);self.assertEqual(read(out/'progress.json')['state'],'stopped')
                files=list((out/'checkpoints').glob('*.json'));stamps={p:p.stat().st_mtime_ns for p in files}
                self.assertEqual(len(files),2);stop.unlink();run(cfg,stop)
                self.assertEqual(read(out/'progress.json')['reused'],2)
                self.assertEqual(stamps,{p:p.stat().st_mtime_ns for p in files})
                run(cfg,stop);self.assertEqual(read(out/'progress.json')['executed'],0)
                self.assertEqual(read(out/'progress.json')['reused'],36)  # 3 baselines + 3 scopes, 3 DIST, 2 modes
                target=files[0];target.write_text('{broken');run(cfg,stop)
                self.assertEqual(read(out/'progress.json')['executed'],1)
                self.assertEqual(read(out/'progress.json')['reused'],35)
                self.assertIn('sha256',read(target))


if __name__=='__main__':unittest.main()
