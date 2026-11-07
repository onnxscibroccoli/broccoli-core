package com.accubook.crm;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.pdf.PdfDocument;
import java.io.IOException;
import java.io.OutputStream;
import java.util.List;

/** Direct, offline Android PDF summary. Separate from editable CSV/ZIP exports. */
public final class QuickReportPdf {
    private static final int WIDTH=612,HEIGHT=792,MARGIN=42;
    private static final int INK=Color.rgb(20,35,54);
    private static final int MUTED=Color.rgb(75,94,111);
    private static final int ACCENT=Color.rgb(19,124,102);
    private QuickReportPdf(){}

    public static void write(List<String> lines,OutputStream output)throws IOException{
        if(lines==null||output==null)throw new IllegalArgumentException("Report output required");
        PdfDocument document=new PdfDocument();
        try{
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
            int pageNumber=0,baseline=0;
            Canvas canvas=null;
            PdfDocument.Page page=null;
            for(String raw:lines){
                String line=raw==null?"":raw.replace('\r',' ').replace('\n',' ')
                    .replace('\t',' ');
                boolean heading=line.contains(" | ");
                paint.setTextSize(heading?13f:12f);
                paint.setTypeface(heading?Typeface.create("sans-serif-medium",Typeface.BOLD):
                    Typeface.create("sans-serif",Typeface.NORMAL));
                List<String> wrapped=wrap(line,paint,WIDTH-2*MARGIN);
                int extra=heading?8:3;
                for(String fragment:wrapped){
                    if(page==null||baseline+22>HEIGHT-MARGIN){
                        if(page!=null){
                            footer(canvas,paint,pageNumber);
                            document.finishPage(page);
                        }
                        pageNumber++;
                        page=document.startPage(new PdfDocument.PageInfo.Builder(
                            WIDTH,HEIGHT,pageNumber).create());
                        canvas=page.getCanvas();
                        paint.setColor(INK);
                        paint.setStyle(Paint.Style.FILL);
                        paint.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));
                        paint.setTextSize(21f);
                        canvas.drawText("ACCUBOOK",MARGIN,65,paint);
                        paint.setTextSize(11f);paint.setColor(ACCENT);
                        canvas.drawText("QUICK FINANCIAL REPORT",MARGIN,86,paint);
                        paint.setStrokeWidth(1.5f);
                        canvas.drawLine(MARGIN,99,WIDTH-MARGIN,99,paint);
                        baseline=125;
                    }
                    paint.setColor(heading?INK:MUTED);
                    paint.setTypeface(Typeface.create("sans-serif",
                        heading?Typeface.BOLD:Typeface.NORMAL));
                    paint.setTextSize(heading?13f:12f);
                    canvas.drawText(fragment,MARGIN,baseline,paint);
                    baseline+=18;
                }
                baseline+=extra;
            }
            if(page==null){
                page=document.startPage(new PdfDocument.PageInfo.Builder(WIDTH,HEIGHT,1).create());
                canvas=page.getCanvas();
                pageNumber=1;
            }
            footer(canvas,paint,pageNumber);
            document.finishPage(page);
            document.writeTo(output);
            output.flush();
        }finally{
            document.close();
        }
    }
    private static List<String> wrap(String source,Paint paint,int available){
        java.util.ArrayList<String> result=new java.util.ArrayList<>();
        if(source.isEmpty()){result.add("");return result;}
        String[] words=source.split(" ",-1);
        StringBuilder line=new StringBuilder();
        for(String word:words){
            String candidate=line.length()==0?word:line+" "+word;
            if(paint.measureText(candidate)<=available){
                line.setLength(0);line.append(candidate);
                continue;
            }
            if(line.length()>0){result.add(line.toString());line.setLength(0);}
            // Break long identifiers safely rather than clipping off the page.
            while(!word.isEmpty()&&paint.measureText(word)>available){
                int end=1;
                while(end<word.length()&&paint.measureText(word,0,end+1)<=available)end++;
                result.add(word.substring(0,end));
                word=word.substring(end);
            }
            line.append(word);
        }
        if(line.length()>0)result.add(line.toString());
        return result;
    }
    private static void footer(Canvas canvas,Paint paint,int pageNumber){
        paint.setColor(MUTED);
        paint.setTypeface(Typeface.create("sans-serif",Typeface.NORMAL));
        paint.setTextSize(9f);
        canvas.drawText("Offline draft summary | Not a reconciled accounting statement",
            MARGIN,HEIGHT-30,paint);
        canvas.drawText(Integer.toString(pageNumber),WIDTH-MARGIN-10,HEIGHT-30,paint);
    }
}
