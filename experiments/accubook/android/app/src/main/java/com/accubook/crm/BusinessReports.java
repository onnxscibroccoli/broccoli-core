package com.accubook.crm;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Offline reporting, not a QuickBooks API integration or general ledger.
 * ReportSelection is an explicit allow-list, never an export-everything default.
 */
public final class BusinessReports {
    public static final String[] SECTIONS={
        "Customers (contact information)",
        "Jobs and invoice values (no payment details)",
        "Estimate / invoice line items",
        "Payments (choose each method)",
        "Expenses (choose each category)",
        "Worker time entries"
    };
    private BusinessReports(){}
    private static List<String> r(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    /**
     * Prevent formula execution in spreadsheet software on user-generated text.
     * Numeric values and dates are exported separately and are not escaped here.
     */
    private static String cell(String input){
        if(input==null)return "";
        int n=0;
        while(n<input.length()&&Character.isWhitespace(input.charAt(n)))n++;
        if(n<input.length()&&("=+-@".indexOf(input.charAt(n))>=0))
            return "'"+input;
        return input;
    }
    private static void put(ZipOutputStream zip,String name,List<List<String>> rows)
        throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }
    public static void export(WorkspaceStore store,CrmWorkspace crm,
                              ReportSelection selection,OutputStream destination)
        throws IOException {
        if(selection==null)throw new IllegalArgumentException("Report selection required");
        try(ZipOutputStream zip=new ZipOutputStream(destination,StandardCharsets.UTF_8)){
            List<WorkspaceStore.Job> jobs=store.jobs();
            if(selection.include(0)){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("CustomerID","CompanyName","ContactName","Phone","Email",
                    "BillingStreet","BillingCity","BillingState","BillingZip"));
                for(WorkspaceStore.Customer c:store.customers())
                    rows.add(r(c.id,cell(c.company),cell(c.contact),cell(c.phone),cell(c.email),
                        cell(c.street),cell(c.city),cell(c.state),cell(c.zip)));
                put(zip,"customers.csv",rows);
            }
            if(selection.include(1)){
                List<List<String>> rows=new ArrayList<>();
                // Do not reveal receipts or balances through a jobs-only selection.
                rows.add(r("DocumentReference","CustomerID","ServiceDate","JobTitle",
                    "JobStatus","DraftAmount"));
                for(WorkspaceStore.Job j:jobs)
                    rows.add(r(DocumentNumbers.reference(j.id,j.date,false),j.customerId,
                        j.date,cell(j.title),j.status,j.total));
                put(zip,"jobs_and_invoices.csv",rows);
            }
            if(selection.include(2)){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("DocumentReference","CustomerID","ServiceDate","Description",
                    "Quantity","UnitRate","LineTotal"));
                for(WorkspaceStore.Job j:jobs)
                    for(WorkspaceStore.LineItem line:store.items(j))
                        rows.add(r(DocumentNumbers.reference(j.id,j.date,false),j.customerId,
                            j.date,cell(line.description),line.quantity,line.unitRate,line.amount));
                put(zip,"invoice_lines.csv",rows);
            }
            if(selection.include(3)){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("PaymentDate","DocumentReference","CustomerID","PaymentMethod",
                    "Amount","Reference","Notes"));
                for(WorkspaceStore.Job j:jobs)
                    for(CrmWorkspace.Payment payment:crm.payments(j))
                        if(selection.payment(payment.method))
                            rows.add(r(payment.date,DocumentNumbers.reference(j.id,j.date,false),
                                j.customerId,payment.method,payment.amount,
                                cell(payment.reference),cell(payment.note)));
                put(zip,"payments_by_method.csv",rows);
            }
            if(selection.include(4)){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("Date","Description","Amount","Category"));
                for(CrmWorkspace.Expense e:crm.expenses())
                    if(selection.expense(e.category))
                        rows.add(r(e.date,cell(e.description),e.amount,cell(e.category)));
                put(zip,"expenses_quickbooks_mapping.csv",rows);
            }
            if(selection.include(5)){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("DocumentReference","Worker","ClockInUTC","ClockOutUTC",
                    "HoursDecimal","WorkNotes"));
                for(WorkspaceStore.Job j:jobs)
                    for(CrmWorkspace.TimeEntry time:crm.timeEntries(j))
                        rows.add(r(DocumentNumbers.reference(j.id,j.date,false),cell(time.worker),
                            time.start,time.end,time.hours,cell(time.note)));
                put(zip,"worker_hours.csv",rows);
            }
            zip.putNextEntry(new ZipEntry("README_IMPORT.txt"));
            String doc="Accubook LOCAL manual accounting extract - "+
                LocalDate.now().toString()+"\n"+
                "Only explicitly selected sections, payment methods and expense categories exist here.\n"+
                "Selected payment methods: "+String.join(", ",selection.methods())+"\n"+
                "Selected expense categories: "+String.join(", ",selection.categories())+"\n"+
                "Jobs and invoice values DO NOT include recorded payment or balance columns.\n"+
                "No bank feed, settlement, tax engine or QuickBooks authentication occurred.\n"+
                "CSV files are generic staging data, NOT a guaranteed QuickBooks import template.\n"+
                "Verify account, tax, transaction sign and column mapping before any import.\n"+
                "User text starting with spreadsheet-formula operators is prefixed with an apostrophe.\n"+
                "Draft values are not proof of legally issued invoices or money collected.\n"+
                "Sensitive selected exports must be stored and shared securely.\n"+
                "Unselected records, GPS traces and full-workspace backups are NOT included.\n";
            zip.write(doc.getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();
            zip.finish();
        }
    }

    /** Short, aggregate-only PDF content; no customer rows or payment references. */
    public static List<String> summary(WorkspaceStore store,CrmWorkspace crm,
                                       ReportSelection selection) throws IOException {
        if(selection==null)throw new IllegalArgumentException("Report selection required");
        List<String> lines=new ArrayList<>();
        lines.add("Date: "+LocalDate.now());
        lines.add("Source: local records (unreconciled; not a tax return)");
        List<WorkspaceStore.Job> jobs=store.jobs();
        if(selection.include(0))
            lines.add("CUSTOMERS | "+store.customers().size()+" saved customer records");
        if(selection.include(1)){
            BigDecimal total=BigDecimal.ZERO;
            for(WorkspaceStore.Job job:jobs)total=total.add(new BigDecimal(job.total));
            lines.add("JOBS | "+jobs.size()+" jobs, draft total $"+total.toPlainString());
            lines.add("No payment totals or balances included in job values.");
        }
        if(selection.include(2)){
            int count=0;
            for(WorkspaceStore.Job job:jobs)count+=store.items(job).size();
            lines.add("INVOICE LINES | "+count+" line items");
        }
        if(selection.include(3)){
            Map<String,BigDecimal> amounts=new LinkedHashMap<>();
            Map<String,Integer> counts=new LinkedHashMap<>();
            for(String method:ReportSelection.PAYMENT_METHODS)
                if(selection.methods().contains(method)){
                    amounts.put(method,BigDecimal.ZERO);
                    counts.put(method,0);
                }
            for(WorkspaceStore.Job job:jobs)
                for(CrmWorkspace.Payment payment:crm.payments(job))
                    if(selection.payment(payment.method)){
                        amounts.put(payment.method,amounts.get(payment.method)
                            .add(new BigDecimal(payment.amount)));
                        counts.put(payment.method,counts.get(payment.method)+1);
                    }
            lines.add("PAYMENTS | selected methods only, manually recorded");
            for(String method:amounts.keySet())
                lines.add(method+" | "+counts.get(method)+" entries | $"+
                    amounts.get(method).toPlainString());
        }
        if(selection.include(4)){
            Map<String,BigDecimal> amounts=new LinkedHashMap<>();
            Map<String,Integer> counts=new LinkedHashMap<>();
            for(String category:selection.categories()){
                amounts.put(category,BigDecimal.ZERO);
                counts.put(category,0);
            }
            for(CrmWorkspace.Expense expense:crm.expenses())
                if(selection.expense(expense.category)){
                    amounts.put(expense.category,amounts.get(expense.category)
                        .add(new BigDecimal(expense.amount)));
                    counts.put(expense.category,counts.get(expense.category)+1);
                }
            lines.add("EXPENSES | selected categories only, manually recorded");
            for(String category:amounts.keySet())
                lines.add(category+" | "+counts.get(category)+" entries | $"+
                    amounts.get(category).toPlainString());
        }
        if(selection.include(5)){
            int count=0;
            BigDecimal hours=BigDecimal.ZERO;
            for(WorkspaceStore.Job job:jobs)
                for(CrmWorkspace.TimeEntry entry:crm.timeEntries(job)){
                    count++;
                    if(!entry.active()&&!entry.hours.isEmpty())
                        hours=hours.add(new BigDecimal(entry.hours));
                }
            lines.add("WORKER TIME | "+count+" entries, completed hours "+
                hours.toPlainString());
        }
        lines.add("Export scope excludes all unselected payments, categories and sections.");
        return lines;
    }
}
