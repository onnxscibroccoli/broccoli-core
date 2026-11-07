package com.accubook.crm;

import android.content.Context;
import android.graphics.*;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;

/**
 * Touch-friendly full rainbow hue spectrum and a large saturation/brightness
 * canvas. Users see colors rather than RGB numbers. Arrow-key accessible.
 */
public final class ColorSpectrumPicker extends View {
    private final float[] hsv={210f,0.72f,0.85f};
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ring=new Paint(Paint.ANTI_ALIAS_FLAG);
    private float left,top,right,gradientBottom,hueTop,hueBottom;
    private final int padding;
    private Runnable callback;
    public ColorSpectrumPicker(Context context,int initial){
        super(context);
        padding=Math.round(getResources().getDisplayMetrics().density*12);
        Color.colorToHSV(initial,hsv);
        setFocusable(true);
        setClickable(true);
        setContentDescription("Color selection spectrum");
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(padding*0.32f);
        updateDescription();
    }
    public void onChanged(Runnable callback){this.callback=callback;}
    public int chosenColor(){return Color.HSVToColor(hsv);}
    public String hex(){
        return String.format(java.util.Locale.ROOT,"#%06X",chosenColor()&0xFFFFFF);
    }
    public void setChosenColor(int color){
        Color.colorToHSV(color,hsv);refresh();
    }
    private void refresh(){
        updateDescription();
        invalidate();
        if(callback!=null)callback.run();
    }
    private void updateDescription(){
        String family;
        float hue=hsv[0];
        if(hue<20||hue>=340)family="red";
        else if(hue<50)family="orange";
        else if(hue<75)family="yellow";
        else if(hue<165)family="green";
        else if(hue<205)family="cyan";
        else if(hue<265)family="blue";
        else if(hue<325)family="purple";else family="pink";
        setContentDescription("Rainbow color picker: "+family+", "+
            Math.round(hsv[1]*100)+" percent saturation, "+
            Math.round(hsv[2]*100)+" percent brightness. "
            +"Drag across the top square or the bottom rainbow strip.");
    }
    @Override protected void onMeasure(int widthMeasureSpec,int heightMeasureSpec){
        int preferred=Math.round(getResources().getDisplayMetrics().density*318);
        int width=MeasureSpec.getSize(widthMeasureSpec);
        int height=resolveSize(preferred,heightMeasureSpec);
        setMeasuredDimension(width,height);
    }
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);
        left=padding;right=getWidth()-padding;
        top=padding;gradientBottom=getHeight()*0.72f;
        hueTop=getHeight()*0.78f;hueBottom=getHeight()-padding;
        int full=Color.HSVToColor(new float[]{hsv[0],1f,1f});
        paint.setShader(new LinearGradient(left,top,right,top,Color.WHITE,full,
            Shader.TileMode.CLAMP));
        canvas.drawRoundRect(left,top,right,gradientBottom,padding,padding,paint);
        paint.setShader(new LinearGradient(left,top,left,gradientBottom,0x00ffffff,
            Color.BLACK,Shader.TileMode.CLAMP));
        canvas.drawRoundRect(left,top,right,gradientBottom,padding,padding,paint);
        paint.setShader(new LinearGradient(left,hueTop,right,hueTop,
            new int[]{0xffff0000,0xffffff00,0xff00ff00,0xff00ffff,
                0xff0000ff,0xffff00ff,0xffff0000},null,Shader.TileMode.CLAMP));
        canvas.drawRoundRect(left,hueTop,right,hueBottom,padding*0.7f,padding*0.7f,paint);
        paint.setShader(null);
        float x=left+(right-left)*hsv[1],y=top+(gradientBottom-top)*(1f-hsv[2]);
        paint.setStyle(Paint.Style.FILL);paint.setColor(Color.WHITE);
        canvas.drawCircle(x,y,padding*0.72f,paint);
        ring.setColor(Color.BLACK);
        canvas.drawCircle(x,y,padding*0.72f,ring);
        float hx=left+(right-left)*(hsv[0]/360f);
        paint.setColor(Color.WHITE);
        canvas.drawCircle(hx,(hueTop+hueBottom)/2f,padding*0.65f,paint);
        ring.setColor(Color.DKGRAY);
        canvas.drawCircle(hx,(hueTop+hueBottom)/2f,padding*0.65f,ring);
    }
    private float bounded(float v){return Math.max(0f,Math.min(1f,v));}
    @Override public boolean onTouchEvent(MotionEvent event){
        if(event.getAction()!=MotionEvent.ACTION_DOWN&&
            event.getAction()!=MotionEvent.ACTION_MOVE&&
            event.getAction()!=MotionEvent.ACTION_UP)
            return super.onTouchEvent(event);
        if(event.getAction()==MotionEvent.ACTION_DOWN)requestFocus();
        float x=bounded((event.getX()-left)/Math.max(1,right-left));
        if(event.getY()>=hueTop){
            hsv[0]=Math.min(359.999f,x*360f);
        }else{
            hsv[1]=x;
            hsv[2]=bounded(1f-(event.getY()-top)/Math.max(1,gradientBottom-top));
        }
        refresh();
        if(event.getAction()==MotionEvent.ACTION_UP)performClick();
        return true;
    }
    @Override public boolean performClick(){super.performClick();return true;}
    @Override public boolean onKeyDown(int keyCode,KeyEvent event){
        switch(keyCode){
            case KeyEvent.KEYCODE_DPAD_LEFT:hsv[0]=(hsv[0]+355)%360;break;
            case KeyEvent.KEYCODE_DPAD_RIGHT:hsv[0]=(hsv[0]+5)%360;break;
            case KeyEvent.KEYCODE_DPAD_UP:hsv[2]=bounded(hsv[2]+0.05f);break;
            case KeyEvent.KEYCODE_DPAD_DOWN:hsv[2]=bounded(hsv[2]-0.05f);break;
            default:return super.onKeyDown(keyCode,event);
        }
        refresh();return true;
    }
}
