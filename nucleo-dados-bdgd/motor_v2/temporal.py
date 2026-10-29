"""Explicit evaluation vintages; reconciled experiments never acquire PIT credentials."""
MODES=('point_in_time','reconciled_retrospective')
def usable(row,origin,mode,training=True):
 if mode not in MODES:raise ValueError('unknown validation mode')
 if row['year']>(origin if training else origin+1):return False
 if row['feature_year']>=row['year']:return False
 if mode=='reconciled_retrospective':return True
 cutoff=f'{origin}-12-31'
 # Historical training examples retain features available at their own forecast origin.
 feature_cutoff=f"{row['feature_year']}-12-31" if training else cutoff
 releases=[row.get('feature_available'),row.get('feature_revision_available')]
 if any(not date or date>feature_cutoff for date in releases):return False
 if training and (not row.get('target_available') or row['target_available']>cutoff):return False
 return True

def label(mode):
 return 'operational_point_in_time' if mode=='point_in_time' else 'retrospective_reconciled_NOT_operational_NOT_leakage_free'
