package com.accubook.crm;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.pdf.PdfDocument;
import java.io.IOException;
import java.io.OutputStream;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Explicit local PDF slips; no customer outreach, auto-send or runtime API. */
public final class ServiceDuePdf {
    private static final int WIDTH=612,HEIGHT=792,MARGIN=42;
    private ServiceDuePdf(){}
    private static void text(Canvas c,Paint p,String value,int x,int y,int maxWidth){
        String line=value==null?"":value.replace('\r',' ').replace('\n',' ');
        if(line.length()>240)line=line.substring(0,240);
        if(p.measureText(line)>maxWidth) {
            while(line.length()>2&&p.measureText(line+"…")>maxWidth)
                line=line.substring(0,line.length()-1);
            line+="…";
        }
        c.drawText(line,x,y,p);
    }
    private static void slip(Canvas canvas,Paint paint,int y,
            RecurringServices.Rule rule,WorkspaceStore.Customer customer){
        paint.setColor(Color.rgb(19,125,103));
        paint.setStrokeWidth(2);
        canvas.drawLine(MARGIN,y,WIDTH-MARGIN,y,paint);
        paint.setTypeface(Typeface.DEFAULT_BOLD);
        paint.setTextSize(16);paint.setColor(Color.rgb(17,43,60));
        text(canvas,paint,rule.label,MARGIN,y+32,WIDTH-2*MARGIN);
        paint.setTypeface(Typeface.DEFAULT);
        paint.setTextSize(13);
        String recipient=customer==null?"Customer ID unavailable":customer.displayName();
        text(canvas,paint,"For: "+recipient,MARGIN,y+63,WIDTH-2*MARGIN);
        text(canvas,paint,"Phone: "+(customer==null?"":customer.phone),
            MARGIN,y+88,WIDTH-2*MARGIN);
        if(!rule.site.isEmpty())
            text(canvas,paint,"Location / equipment: "+rule.site,
                MARGIN,y+113,WIDTH-2*MARGIN);
        paint.setTypeface(Typeface.DEFAULT_BOLD);
        text(canvas,paint,"Next due: "+(rule.dueDate.isEmpty()?"Odometer only":rule.dueDate),
            MARGIN,y+153,WIDTH-2*MARGIN);
        if(!rule.dueMiles.isEmpty())
            text(canvas,paint,"Mileage target: "+rule.dueMiles,
                MARGIN,y+180,WIDTH-2*MARGIN);
        paint.setTypeface(Typeface.DEFAULT);
        paint.setTextSize(11);
        paint.setColor(Color.rgb(84,96,109));
        text(canvas,paint,"Last completed: "+rule.lastDate+
            " · Verify service history before contacting.",MARGIN,y+222,WIDTH-2*MARGIN);
        text(canvas,paint,"Local reminder · Not proof of service or a payment request.",
            MARGIN,y+245,WIDTH-2*MARGIN);
    }
    public static void write(String business,List<RecurringServices.Rule> due,
            Map<String,WorkspaceStore.Customer> customers,OutputStream out)
        throws IOException{
        if(due==null||due.isEmpty()||out==null)
            throw new IllegalArgumentException("Select at least one service due by date");
        if(due.size()>500)throw new IOException("Print up to 500 slips at a time");
        PdfDocument pdf=new PdfDocument();
        try{
            Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
            for(int offset=0;offset<due.size();offset+=2){
                PdfDocument.Page page=pdf.startPage(
                    new PdfDocument.PageInfo.Builder(WIDTH,HEIGHT,offset/2+1).create());
                Canvas canvas=page.getCanvas();
                canvas.drawColor(Color.WHITE);
                p.setTypeface(Typeface.DEFAULT_BOLD);
                p.setTextSize(20);p.setColor(Color.rgb(17,43,60));
                text(canvas,p,business==null||business.isEmpty()?"Accubook":business,
                    MARGIN,51,WIDTH-2*MARGIN);
                p.setTextSize(11);p.setTypeface(Typeface.DEFAULT);
                canvas.drawText("DUE SERVICE SLIPS · "+LocalDate.now(),MARGIN,76,p);
                RecurringServices.Rule first=due.get(offset);
                slip(canvas,p,100,first,customers.get(first.customerId));
                if(offset+1<due.size()){
                    RecurringServices.Rule second=due.get(offset+1);
                    slip(canvas,p,438,second,customers.get(second.customerId));
                }
                p.setTextSize(10);p.setColor(Color.DKGRAY);
                canvas.drawText("Generated offline. No messages have been sent.",
                    MARGIN,HEIGHT-28,p);
                pdf.finishPage(page);
            }
            pdf.writeTo(out);out.flush();
        }finally{pdf.close();}
    }
}
