package com.accubook.crm;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.pdf.PdfDocument;
import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * One-tap local, print-ready accounting SUMMARY. The same explicit section,
 * method and expense-category allow-list as the CSV ZIP applies to every row.
 * No accounting service is connected; this is not an audited general ledger.
 */
public final class FinancialReportPdf {
    private FinancialReportPdf(){}
    private static final int WIDTH=612, HEIGHT=792, LEFT=43, RIGHT=569;
    private static final int NAVY=Color.rgb(18,45,74);
    private static final int INK=Color.rgb(26,36,52);
    private static final int GRAY=Color.rgb(79,94,111);
    private static final int TEAL=Color.rgb(16,125,130);

    private static final class Writer {
        final PdfDocument document=new PdfDocument();
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Canvas canvas;
        int page=0;
        float y=0;
        String title;
        Writer(String company){title=company==null||company.trim().isEmpty()?"Accubook":company;}
        void newPage(){
            if(canvas!=null)document.finishPage(current);
            page++;
            current=document.startPage(new PdfDocument.PageInfo.Builder(
                WIDTH,HEIGHT,page).create());
            canvas=current.getCanvas();y=53;
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(NAVY);
            canvas.drawRect(0,0,WIDTH,25,paint);
            writeLine(title+"  |  Financial report",16,NAVY,true);
            y+=5;
            writeLine("Generated "+LocalDate.now()+"   |   Local records; no bank reconciliation",9,GRAY,false);
            y+=16;
        }
        PdfDocument.Page current;
        void ensure(float need){if(canvas==null||y+need>HEIGHT-56)newPage();}
        void writeLine(String line,float size,int color,boolean bold){
            ensure(size+10);
            paint.setColor(color);
            paint.setTextSize(size);
            paint.setTypeface(bold?android.graphics.Typeface.create(
                android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD):
                android.graphics.Typeface.DEFAULT);
            String remaining=line==null?"":line.replace('\n',' ').replace('\r',' ');
            int attempts=0;
            do{
                ensure(size+11);
                int count=paint.breakText(remaining,true,RIGHT-LEFT,null);
                if(count<=0)break;
                if(count<remaining.length()){
                    int blank=remaining.lastIndexOf(' ',count-1);
                    if(blank>count/2)count=blank+1;
                }
                canvas.drawText(remaining.substring(0,count).trim(),LEFT,y,paint);
                y+=size+6;
                remaining=remaining.substring(count).trim();
            }while(!remaining.isEmpty()&&++attempts<200);
        }
        void header(String name){y+=9;writeLine(name,12,TEAL,true);y+=3;}
        void item(String label,String total){writeLine(label+"     "+total,10,INK,false);}
        void close(OutputStream destination)throws IOException {
            if(current!=null)document.finishPage(current);
            try{document.writeTo(destination);destination.flush();}
            finally{document.close();}
        }
    }
    public static void export(WorkspaceStore store,CrmWorkspace crm,
                              ExportSelection selection,OutputStream destination)
        throws IOException {
        Writer w=new Writer(crm.branding().business);
        w.newPage();
        w.writeLine("REPORT SCOPE (explicitly selected)",11,NAVY,true);
        for(int i=0;i<BusinessReports.SECTIONS.length;i++)
            if(selection.included(i))
                w.writeLine("Included: "+BusinessReports.SECTIONS[i],9,GRAY,false);
        if(selection.included(3))
            w.writeLine("Payment methods: "+selection.paymentMethods,9,GRAY,false);
        if(selection.included(4))
            w.writeLine("Expense categories: "+selection.expenseCategories,9,GRAY,false);
        List<WorkspaceStore.Job> jobs=store.jobs();
        if(selection.included(0)){
            w.header("Customers");
            for(WorkspaceStore.Customer customer:store.customers())
                w.item(customer.displayName(),customer.city+" "+customer.state);
        }
        if(selection.included(1)){
            w.header("Jobs and recorded invoice totals");
            BigDecimal total=BigDecimal.ZERO,received=BigDecimal.ZERO;
            for(WorkspaceStore.Job job:jobs){
                w.item(job.date+" / "+job.title, "$"+job.total+"  ["+job.status+"]");
                total=total.add(new BigDecimal(job.total));
                received=received.add(crm.received(job));
            }
            w.item("Total job value","$"+total.toPlainString());
            w.item("All recorded receipts (not filtered by method)",
                "$"+received.toPlainString());
            w.item("Open balance (not a bank balance)",
                "$"+total.subtract(received).toPlainString());
        }
        if(selection.included(2)){
            w.header("Estimate / invoice line items");
            for(WorkspaceStore.Job job:jobs)
                for(WorkspaceStore.LineItem item:store.items(job))
                    w.item(job.title+" / "+item.description,
                        item.quantity+" x $"+item.unitRate+" = $"+item.amount);
        }
        if(selection.included(3)){
            w.header("Selected payment-method ledgers");
            Map<String,BigDecimal> totals=new LinkedHashMap<>();
            for(String method:selection.paymentMethods)totals.put(method,BigDecimal.ZERO);
            for(WorkspaceStore.Job job:jobs)
                for(CrmWorkspace.Payment payment:crm.payments(job))
                    if(selection.includesPayment(payment.method))
                        totals.put(payment.method,totals.get(payment.method)
                            .add(new BigDecimal(payment.amount)));
            for(Map.Entry<String,BigDecimal> row:totals.entrySet())
                w.item(row.getKey(),"$"+row.getValue().toPlainString());
        }
        if(selection.included(4)){
            w.header("Selected expense categories");
            Map<String,BigDecimal> expenses=new LinkedHashMap<>();
            for(String category:selection.expenseCategories)
                expenses.put(category,BigDecimal.ZERO);
            for(CrmWorkspace.Expense expense:crm.expenses())
                if(selection.includesExpense(expense.category))
                    expenses.put(expense.category,expenses.get(expense.category)
                        .add(new BigDecimal(expense.amount)));
            for(Map.Entry<String,BigDecimal> entry:expenses.entrySet())
                w.item(entry.getKey(),"$"+entry.getValue().toPlainString());
        }
        if(selection.included(5)){
            w.header("Worker hours recorded");
            for(WorkspaceStore.Job job:jobs)
                for(CrmWorkspace.TimeEntry entry:crm.timeEntries(job))
                    w.item(job.title+" / "+entry.worker,entry.hours+" hours");
        }
        w.header("Important limitations");
        w.writeLine("This document summarizes user-entered data only. It is not a tax return, "
            +"payroll register, verified payment settlement, legally issued invoice, "
            +"or reconciled double-entry general ledger. Verify before submitting.",9,GRAY,false);
        w.close(destination);
    }
}
