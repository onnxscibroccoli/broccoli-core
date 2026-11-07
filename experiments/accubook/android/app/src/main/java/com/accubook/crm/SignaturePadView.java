package com.accubook.crm;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.MotionEvent;
import android.view.View;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

/**
 * Local-only explicit finger/stylus signature pad; does not open the camera,
 * request permissions, or claim verified legal identity.
 */
public final class SignaturePadView extends View {
    private final Path path=new Path();
    private final Paint line=new Paint(Paint.ANTI_ALIAS_FLAG);
    private boolean drawn=false;
    public SignaturePadView(Context context){
        super(context);
        setBackgroundColor(Color.WHITE);
        line.setColor(Color.rgb(18,35,52));
        line.setStrokeWidth(dp(3));
        line.setStyle(Paint.Style.STROKE);
        line.setStrokeJoin(Paint.Join.ROUND);
        line.setStrokeCap(Paint.Cap.ROUND);
        setMinimumHeight(dp(180));
        setContentDescription("Signature drawing pad. Use finger or stylus. "
            +"Name and signature are stored only in this job.");
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);
        canvas.drawColor(Color.WHITE);
        canvas.drawPath(path,line);
    }
    @Override public boolean onTouchEvent(MotionEvent event){
        float x=Math.max(0,Math.min(getWidth(),event.getX()));
        float y=Math.max(0,Math.min(getHeight(),event.getY()));
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                path.moveTo(x,y); drawn=true;invalidate();return true;
            case MotionEvent.ACTION_MOVE:
                path.lineTo(x,y);invalidate();return true;
            case MotionEvent.ACTION_UP:
                path.lineTo(x,y);invalidate();performClick();return true;
            case MotionEvent.ACTION_CANCEL:return true;
            default:return false;
        }
    }
    @Override public boolean performClick(){super.performClick();return true;}
    public void clear(){path.reset();drawn=false;invalidate();}
    public boolean hasInk(){return drawn;}
    public byte[] png()throws IOException{
        if(!drawn || getWidth()<64 || getHeight()<40)
            throw new IOException("Please sign inside the white box");
        Bitmap bitmap=Bitmap.createBitmap(getWidth(),getHeight(),Bitmap.Config.ARGB_8888);
        try{
            Canvas canvas=new Canvas(bitmap);
            canvas.drawColor(Color.WHITE);
            canvas.drawPath(path,line);
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            if(!bitmap.compress(Bitmap.CompressFormat.PNG,100,bytes))
                throw new IOException("Signature PNG could not be encoded");
            return bytes.toByteArray();
        }finally{bitmap.recycle();}
    }
}
