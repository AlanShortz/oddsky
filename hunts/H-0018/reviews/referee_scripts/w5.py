import numpy as np, pandas as pd, os, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd, wb
R=hd.RUNS
rng=np.random.default_rng(5)
path=f'{R}/data/elbadry/cat.parquet'
# === Oort: replicate with factor, solar reflex, constant term
raw=wb.load(path,False)
s=raw[(raw.parallax1>2)&(raw.parallax1/raw.parallax_error1>20)].drop_duplicates('source_id1')
ve,vn=wb.basis(s.ra1.values,s.dec1.values)
nv=wb.unit(s.ra1.values,s.dec1.values); r_i=nv*(1000/s.parallax1.values)[:,None]
vt=4.74047*(ve*s.pmra1.values[:,None]+vn*s.pmdec1.values[:,None])/s.parallax1.values[:,None]
from astropy.coordinates import SkyCoord
import astropy.units as u
# solar motion wrt mean sample in ICRS: estimated by LSQ of vt on projection
# gal to icrs matrix via astropy
gx=SkyCoord(l=[0,90,0]*u.deg,b=[0,0,90]*u.deg,frame='galactic').icrs.cartesian.xyz.value.T  # rows: x,y,z gal axes in ICRS
# LSQ: vt = -(I-nn^T) v_sun
N=len(s);AtA=np.eye(3)*N-(nv[:,:,None]*nv[:,None,:]).sum(0);Atb=-vt.sum(0)  # since proj of vt = vt
vs=np.linalg.solve(AtA,Atb);print('fitted solar motion (ICRS)',vs,' Galactic UVW',gx@vs)
vt_cor=vt+(vs-(nv*vs).sum(1,keepdims=True)*nv)
def run(vel,label,Nd=6000000):
    out=[]
    for rmin,rmax in [(30,60),(60,100),(100,150),(150,220),(220,320)]:
        cand=rng.integers(0,N,Nd);i=rng.integers(0,N,Nd)
        sep=np.linalg.norm(r_i[cand]-r_i[i],axis=1);ok=(sep>rmin)&(sep<rmax)&(cand!=i)
        i,j=i[ok],cand[ok];mid=r_i[i]+r_i[j];mid/=np.linalg.norm(mid,axis=1,keepdims=True);r=r_i[j]-r_i[i];dv=vel[j]-vel[i]
        rp=r-(r*mid).sum(1,keepdims=True)*mid;ins=np.linalg.norm(rp,axis=1)>.7*np.linalg.norm(r,axis=1)
        r,dv,mid,rp=r[ins],dv[ins],mid[ins],rp[ins]
        z=(np.cross(rp,dv)*mid).sum(1);ra=np.degrees(np.arctan2(mid[:,1],mid[:,0]))%360;dec=np.degrees(np.arcsin(mid[:,2]))
        ng=hd.gal_vectors(ra,dec);f=hd.fit_dipole(np.sign(z),ng);rr=np.linalg.norm(rp,axis=1)
        t=(np.cross(mid,rp/rr[:,None])*dv).sum(1)
        sg=np.std(t[np.abs(t)<100]);
        # empirical 2f(0)
        bw=3.0;f0=(np.abs(t)<bw).mean()/(2*bw);fac=2*f0
        hb=np.abs(ng[:,2])>.5;f0h=(np.abs(t[hb])<bw).mean()/(2*bw);sgh=np.std(t[hb][np.abs(t[hb])<100])
        W=ng[:,2]**2;f0w=np.average(np.abs(t)<bw,weights=W)/(2*bw)
        Bgauss=f['Dz']*sg/(.7979*rr.mean())*1000;Bemp=f['Dz']/(2*f0w*np.average(rr,weights=W))*1000
        print(f'{label} r{rmin}-{rmax} N={f["N"]} Dx={100*f["Dx"]:+.2f} Dy={100*f["Dy"]:+.2f} Dz={100*f["Dz"]:+.2f}±{100*f["Dz_se"]:.2f}  sig={sg:.1f} fac_gauss={.7979/sg:.4f} 2f0={fac:.4f} 2f0(|nz|>.5)={2*f0h:.4f} sig(|nz|>.5)={sgh:.1f}  2f0(nz^2 wt)={2*f0w:.4f}  B_gauss={Bgauss:+.1f} B_emp={Bemp:+.1f}±{f["Dz_se"]/(2*f0w*rr.mean())*1000:.1f}  kurt={stats.kurtosis(t[np.abs(t)<100]):.2f}')
        out.append((rr.mean(),f['Dz'],f['Dz_se'],f['Dy'],f['Dy_se'],f['Dx']))
    o=np.array(out)
    X=np.column_stack([np.ones(5),o[:,0]/1000]);w=1/o[:,2]**2
    b=np.linalg.solve((X.T*w)@X,(X.T*w)@o[:,1]);cov=np.linalg.inv((X.T*w)@X)
    print(f'  fit Dz = a + b*r: a={100*b[0]:+.2f}±{100*np.sqrt(cov[0,0]):.2f}%, slope={100*b[1]:+.2f}±{100*np.sqrt(cov[1,1]):.2f}%/kpc; through-origin B-scale reduction factor at r=248: {b[1]*.248/o[-1,1]:.2f}')
run(vt,'raw')
run(vt_cor,'solar-corrected')
# === WB realistic mock gain with real pair errors
heldraw=wb.load(path,True)
z,sig,n=wb.rotation(heldraw)
print('\nselected frac real',np.mean(np.abs(z)>3*sig),'N',(np.abs(z)>3*sig).sum())
d=heldraw
# Kepler draw for each pair: thermal e, random orientation, random phase. Scale a so that projected sep matches observed
N=min(len(d),200000);idx=rng.choice(len(d),N,replace=False)
dd=d.iloc[idx];sg=sig[idx];nn=n[idx]
s_ang=dd.pairdistance.values*np.pi/180  # rad
plx=dd.parallax1.values
s_au=dd.sep_AU.values
def kepler_draw(M_tot):
    e=np.sqrt(rng.random(N));M=rng.uniform(0,2*np.pi,N);E=M+e*np.sin(M)
    for _ in range(8):E=E-(E-e*np.sin(E)-M)/(1-e*np.cos(E))
    xo,yo=np.cos(E)-e,np.sqrt(1-e**2)*np.sin(E);vx=-np.sin(E)/(1-e*np.cos(E));vy=np.sqrt(1-e**2)*np.cos(E)/(1-e*np.cos(E))
    # random orientation in observer frame: los axis = 3rd axis
    L=rng.normal(size=(N,3));L/=np.linalg.norm(L,axis=1,keepdims=True)
    t=np.cross(L,rng.normal(size=(N,3)));t/=np.linalg.norm(t,axis=1,keepdims=True);q=np.cross(L,t)
    r3=t*xo[:,None]+q*yo[:,None];v3=t*vx[:,None]+q*vy[:,None]  # L along t x q = L (check) 
    rs=np.hypot(r3[:,0],r3[:,1]);a=s_au/rs  # au
    vscale=np.sqrt(M_tot*887.1/a)*1.0  # km/s: sqrt(GM/a), G=887.1 km2/s2 au/Msun
    zsky=(r3[:,0]*v3[:,1]-r3[:,1]*v3[:,0])  # (r x v).los, dimensionless, r in a-units
    # physical: s_au * v_t where v_t = zsky/rs * vscale; convert to rad*mas/yr: s_ang * (v_t/4.74047*plx)
    vt=zsky/rs*vscale
    zz=s_ang*vt/4.74047*plx
    return L,zz,zsky
for Mt in [1.5,2.0]:
    L,zz,zsky=kepler_draw(Mt)
    y0=np.sign(zsky)
    # check: y = sign(L.los)
    print('M',Mt,'sign check',np.mean(y0==np.sign(L[:,2])))
    obs=zz+rng.normal(0,sg)
    keep=np.abs(obs)>3*sg
    print('  mock selected fraction %.3f; real %.3f ; ratio real/mock %.2f'%(keep.mean(),np.mean(np.abs(z)>3*sig),np.mean(np.abs(z)>3*sig)/keep.mean()))
    yo=np.sign(obs)
    print('  sign agreement among selected %.4f'%np.mean(yo[keep]==y0[keep]))
    # gain: distribution p(L)=1+3 mu L_Z. Using reweight: L in observer frame: los=n, so L.n = L[:,2], Z-direction component along n=nn_z; L_Z=? L_Z = L[:,2]*nz + sqrt(1-nz^2)*perp comp, perp: use L[:,0] random azimuth
    nz=nn[:,2]
    LZ=L[:,2]*nz+np.sqrt(1-nz**2)*L[:,0]
    mu=0.01;w=1+3*mu*LZ
    X=np.column_stack([np.ones(keep.sum()),nn[keep]]);W=w[keep]
    beta=np.linalg.lstsq(X*np.sqrt(W)[:,None],yo[keep]*np.sqrt(W),rcond=None)[0]
    beta0=np.linalg.lstsq(X,yo[keep],rcond=None)[0]
    print('  gain D_Z/<L_Z> = %.2f  (no selection: 1.5 expected)'%((beta[3]-beta0[3])/mu))
    # by bin
    for lo,hi in wb.BINS[:4]:
        k=keep&(s_au>=lo)&(s_au<hi)
        if k.sum()<500: continue
        X=np.column_stack([np.ones(k.sum()),nn[k]]);W=w[k]
        b1=np.linalg.lstsq(X*np.sqrt(W)[:,None],yo[k]*np.sqrt(W),rcond=None)[0];b0=np.linalg.lstsq(X,yo[k],rcond=None)[0]
        print('   bin %.0e gain %.2f selected %d'%(lo,(b1[3]-b0[3])/mu,k.sum()))
# real pairs: non-Keplerian fraction among selected
sel=np.abs(z)>3*sig
dv=np.abs(z[sel])/(dd.pairdistance.values[0]*0+1)
s_angall=d.pairdistance.values[sel]*np.pi/180
vt=np.abs(z[sel])/s_angall/d.parallax1.values[sel]*4.74047  # km/s tangential
vc=np.sqrt(2*887.1/d.sep_AU.values[sel])  # circular for 2 Msun at s
for f in [1,1.5,2,3]:
    print('selected with v_t > %.1f*v_c(2Msun): %.3f'%(f,np.mean(vt>f*vc)))
print('escape speed bound: v_t > sqrt2 v_c cannot be bound if s=r, frac %.3f'%np.mean(vt>np.sqrt(2)*vc))
# dilution by those: D_Z and sign among them
ysel=np.sign(z[sel]);nsel=n[sel]
for lo,hi,lab in [(0,np.sqrt(2),'v_t<=sqrt2 vc'),(np.sqrt(2),3,'sqrt2-3'),(3,1e9,'>3')]:
    k=(vt>=lo*vc)&(vt<hi*vc);f=hd.fit_dipole(ysel[k],nsel[k]);print(hd.fmt(lab,f))
# PA anisotropy & frame-spin coupling: E[y]=m+D.n+S.shat (in Galactic)
mid=wb.unit(d.ra1.values,d.dec1.values);
n1,n2=wb.unit(d.ra1.values,d.dec1.values),wb.unit(d.ra2.values,d.dec2.values)
r=n2-n1;r/=np.linalg.norm(r,axis=1,keepdims=True)
# swap sign: z is swap-invariant; r flips: a spin term has y~-sign(r.dw)*... Make antisymmetric by Star order: use brighter-fainter order
ga,gb=d.phot_g_mean_mag1.values,d.phot_g_mean_mag2.values
ord_=np.where(ga<gb,1.0,-1.0)  # r from bright to faint
rb=r*ord_[:,None]
rg=SkyCoord(x=rb[:,0],y=rb[:,1],z=rb[:,2],representation_type='cartesian',frame='icrs').galactic.cartesian.xyz.value.T
X=np.column_stack([np.ones(sel.sum()),n[sel],rg[sel]])
beta=np.linalg.lstsq(X,ysel,rcond=None)[0];res=ysel-X@beta;XtXi=np.linalg.inv(X.T@X);cov=XtXi@((X*res[:,None]).T@(X*res[:,None]))@XtXi;se=np.sqrt(np.diag(cov))
print('\nD + spin term (r bright->faint): D=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%%  S=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%%'%tuple(np.ravel([[100*beta[i],100*se[i]] for i in range(1,7)])))
# PA isotropy by hemisphere
xy=rg[sel]; print('mean |r.Z| near plane etc: correlation r_Z^2 vs n_Z:',np.corrcoef(xy[:,2]**2,n[sel][:,2])[0,1])
