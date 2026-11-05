import sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import numpy as np
def halftone(src,out,width,cell,palette,gamma=1.0,thresh=0.06,sun=None,scan=None,crop=None):
    im=Image.open(src).convert('RGB')
    if crop: im=im.crop(crop)
    h=int(im.height*width/im.width); im=im.resize((width,h),Image.LANCZOS)
    rgb=np.asarray(im).astype(float)/255
    L=(0.3*rgb[...,0]+0.59*rgb[...,1]+0.11*rgb[...,2])
    S=4; W,H=width*S,h*S
    canvas=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(canvas)
    lo=np.array(palette[0]);hi=np.array(palette[1])
    for y in range(0,h,cell):
        for x in range(0,width,cell):
            blk=L[y:y+cell,x:x+cell]; v=blk.mean()
            if v<thresh: continue
            v=min(1,(v-thresh)/(1-thresh))**gamma
            r=cell/2*1.18*np.sqrt(v)
            if r<0.35: continue
            pr=rgb[y:y+cell,x:x+cell].reshape(-1,3).mean(0)
            if sun is not None and pr[0]>0.55 and pr[0]-pr[2]>0.35:
                col=tuple(sun)
            else:
                col=tuple((lo+(hi-lo)*v).astype(int))
            cx,cy=(x+cell/2)*S,(y+cell/2)*S
            if scan and ((y>h*scan and (y//cell)%2==0) or (h*0.40<y<h*0.43)):
                d.rectangle([x*S,cy-r*S*0.45,(x+cell)*S,cy+r*S*0.45],fill=col+(255,))
            else:
                d.ellipse([cx-r*S,cy-r*S,cx+r*S,cy+r*S],fill=col+(255,))
    canvas=canvas.resize((width,h),Image.LANCZOS)
    canvas.save(out); print(out,canvas.size)
if __name__=='__main__':
    cream=[(150,112,62),(244,228,190)]
    ink=[(70,80,110),(22,30,56)]
    halftone('_src/bust-src.jpg','assets/bust.png',900,5,cream,gamma=1.25,thresh=0.10,scan=0.66,crop=(100,120,700,1000))
    halftone('_src/fastfetch-emblem-justice.png','assets/emblem.png',420,4,cream,gamma=0.75,thresh=0.10,sun=(201,86,52))
