exec(open('/tmp/ref_h18/a1b.py').read().split("pd.set_option")[0])
g=m[(m.pr>0.7)&(m.pr<1.4)].copy()
ind=g[np.abs(g.pr-1)>0.01]
print('period-matched',len(g),'agree',(g.y==g.pred).sum(),'agree frac %.3f'%(g.y==g.pred).mean())
print('|P_orb6/P_gaia -1|>1%: N',len(ind),'agree',(ind.y==ind.pred).sum())
i2=ind[np.abs(ind.inc-90)>10];print(' and |i-90|>10: N',len(i2),'agree',(i2.y==i2.pred).sum())
for ty,gg in i2.groupby('nss_solution_type'): print('  ',ty,len(gg),(gg.y==gg.pred).sum())
# flipped convention p-value
from scipy.stats import binomtest
print(' binom p vs 0.5:',binomtest(int((i2.y==i2.pred).sum()),len(i2),.5).pvalue)
print(' Earth-sense check: i>90 means y=+1 ; share of orb6 i>90',(i2.inc>90).mean())
