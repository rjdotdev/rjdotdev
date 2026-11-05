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

def make_bust_light(src='_src/bust-src.jpg', out='assets/bust-light.png', crop=(100,120,700,1000)):
    """Soft charcoal/sepia duotone for paper panels, with gentle highlight fade to paper."""
    from PIL import ImageOps
    import tempfile, os
    sepia=[(48,38,28),(152,128,98)]
    tmp=out+'.base.png'
    halftone(src,tmp,900,5,sepia,gamma=1.02,thresh=0.08,scan=0.66,crop=crop)
    im=Image.open(src).convert('RGB')
    if crop: im=im.crop(crop)
    w=900; h=int(im.height*w/im.width); im=im.resize((w,h),Image.LANCZOS)
    L=np.asarray(ImageOps.grayscale(im)).astype(float)/255
    base=np.asarray(Image.open(tmp).convert('RGBA')).astype(float)
    fade=np.clip((L-0.52)/0.38,0,1)
    base[...,3]*=(1-0.40*fade)
    Image.fromarray(base.astype(np.uint8),'RGBA').save(out)
    os.remove(tmp); print(out, Image.open(out).size)


def make_emblem_light(src='_src/fastfetch-emblem-justice.png', out='assets/emblem-light.png'):
    """Crisp sepia/charcoal Lady Justice + muted rust halo for paper.

    Higher source width than display, hard-edged dots (no soft alpha glow).
    """
    import os
    from PIL import ImageFilter
    sepia=[(42,34,26),(148,124,94)]
    rust=(168,92,54)
    halftone(src, out, 840, 3, sepia, gamma=0.95, thresh=0.06, sun=rust)
    im=Image.open(out).convert('RGBA')
    a=np.asarray(im).astype(np.float32)
    alpha=a[...,3]
    hard=np.where(alpha < 48, 0, np.clip(200 + alpha*0.22, 0, 255))
    a[...,3]=hard
    rgb_img=Image.fromarray(a.astype(np.uint8),'RGBA').convert('RGB').filter(
        ImageFilter.UnsharpMask(radius=0.8, percent=120, threshold=4))
    final=np.dstack([np.asarray(rgb_img), hard.astype(np.uint8)])
    Image.fromarray(final,'RGBA').save(out)
    print(out, Image.open(out).size)


if __name__=='__main__':
    cream=[(150,112,62),(244,228,190)]
    halftone('_src/bust-src.jpg','assets/bust.png',900,5,cream,gamma=1.25,thresh=0.10,scan=0.66,crop=(100,120,700,1000))
    make_bust_light()
    halftone('_src/fastfetch-emblem-justice.png','assets/emblem.png',420,4,cream,gamma=0.75,thresh=0.10,sun=(201,86,52))
    make_emblem_light()
