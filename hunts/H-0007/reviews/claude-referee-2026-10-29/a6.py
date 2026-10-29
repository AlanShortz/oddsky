import numpy as np
K=4*np.pi*4.30091e-3/(2.99792458e5**2)  # pc / Msun
R0,zs=8200.,20.
def rho(D,l,b):
    l,b=np.radians(l),np.radians(b)
    x=R0-D*np.cos(b)*np.cos(l); y=D*np.cos(b)*np.sin(l); z=zs+D*np.sin(b); R=np.hypot(x,y)
    thin=0.043*np.exp(-(R-R0)/2600)*np.exp(-np.abs(z)/300)
    thick=0.043*0.12*np.exp(-(R-R0)/2000)*np.exp(-np.abs(z)/900)
    # crude bar/bulge for inner lines of sight (Dwek-like, 8.5 Msun/pc3 central, scale 1 kpc)
    r=np.sqrt(x**2+y**2+(z/0.6)**2); bul=1.5*np.exp(-0.5*(r/700)**2)
    return thin+thick+bul
def tau(l,b,Ds):
    D=np.linspace(1,Ds-1,4000); return K*np.trapezoid(rho(D,l,b)*D*(Ds-D)/Ds,D)
for lab,l,b,Ds in [('J040025 (3.0 kpc)',162.8,-15.3,3000),('J040025 (3.4 kpc)',162.8,-15.3,3400),('same l,b at 1 kpc',162.8,-15.3,1000),
                   ('J185744 Gaia DR3 4084984459435880064 (6 kpc)',14.9,-10.6,6000),('Kojima-1 like (l=178,b=-10, 0.8 kpc)',178.,-10.,800)]:
    tt=tau(l,b,Ds); 
    for tE in [20,40]:
        G=2/np.pi*tt/tE*365.25
        print(f'{lab:48s} tau={tt:.2e}  tE={tE}d: rate={G:.1e}/yr/star; P(A>=2.73 in one snapshot)={tt*0.384**2:.1e}')
