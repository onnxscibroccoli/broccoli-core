package com.accubook.crm;

import android.content.Context;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * One search across local contacts, customers, jobs, notes, invoice references,
 * material requests, custom fields, payment references and the optional catalog.
 * Scans on explicit request only: no network, no index of private data, no sync.
 * Call outside the UI thread for large workspaces.
 */
public final class UniversalLookup {
    public static final class Match {
        public final String kind,id,title,detail;
        public final int score;
        Match(String kind,String id,String title,String detail,int score){
            this.kind=kind;this.id=id;this.title=title;this.detail=detail;this.score=score;
        }
    }
    private final WorkspaceStore store;
    private final CrmWorkspace crm;
    private final Context context;
    public UniversalLookup(Context context,WorkspaceStore store,CrmWorkspace crm){
        this.context=context;this.store=store;this.crm=crm;
    }
    private static String combined(List<String> parts){
        StringBuilder out=new StringBuilder();
        for(String part:parts)out.append(part).append(' ');
        return out.toString();
    }
    private static void add(List<Match> found,String query,String kind,String id,
            String title,String detail,String... fields){
        int score=SearchTerms.score(query,title,fields);
        if(score>0)found.add(new Match(kind,id,title,detail,score));
    }
    public List<Match> search(String query)throws IOException{
        List<Match> found=new ArrayList<>();
        if(SearchTerms.normalize(query).length()<2)return found;
        List<WorkspaceStore.Customer> customers=store.customers();
        Map<String,WorkspaceStore.Customer> customerById=new HashMap<>();
        for(WorkspaceStore.Customer c:customers){
            customerById.put(c.id,c);
            add(found,query,"CUSTOMER",c.id,c.displayName(),
                "Customer · "+c.phone,
                c.id,c.displayName(),c.company,c.contact,c.phone,c.email,
                c.street,c.city,c.state,c.zip);
        }
        for(ContactDirectory.Contact contact:new ContactDirectory(store).all()){
            add(found,query,"CONTACT",contact.id,contact.name,
                "Contact · "+contact.phone,
                contact.id,contact.name,contact.phone,contact.email,contact.customerId);
        }
        JobTemplates templates=new JobTemplates(store);
        for(WorkspaceStore.Job job:store.jobs()){
            WorkspaceStore.Customer customer=customerById.get(job.customerId);
            List<String> terms=new ArrayList<>();
            terms.add(job.id);terms.add(job.title);terms.add(job.street);
            terms.add(job.city);terms.add(job.state);terms.add(job.zip);
            terms.add(job.date);terms.add(job.status);terms.add(job.customerId);
            terms.add(DocumentNumbers.reference(job.id,job.date,false));
            terms.add(DocumentNumbers.reference(job.id,job.date,true));
            if(customer!=null){
                terms.add(customer.displayName());terms.add(customer.phone);
                terms.add(customer.email);terms.add(customer.street);
            }
            for(WorkspaceStore.LineItem line:store.items(job)){
                terms.add(line.id);terms.add(line.description);
            }
            terms.add(store.fieldNotes(job));
            for(WorkspaceStore.MaterialRequest request:store.materialRequests(job)){
                terms.add(request.id);terms.add(request.description);
                terms.add(request.unit);terms.add(request.status);
            }
            File folder=store.directoryForJob(job);
            if(new File(folder,"custom_fields.csv").isFile()){
                for(JobTemplates.Field field:templates.forJob(job)){
                    terms.add(field.label);terms.add(field.value);
                }
            }
            if(new File(folder,"payments.csv").isFile()){
                for(CrmWorkspace.Payment payment:crm.payments(job)){
                    terms.add(payment.id);terms.add(payment.reference);
                    terms.add(payment.method);terms.add(payment.note);
                }
            }
            if(new File(folder,"change_orders.csv").isFile() &&
                new File(folder,"change_order_lines.csv").isFile()){
                ChangeOrders changes=new ChangeOrders(store);
                for(ChangeOrders.Order order:changes.orders(job)){
                    terms.add(order.id);terms.add(order.title);
                    for(ChangeOrders.Line line:changes.lines(job,order))
                        terms.add(line.description);
                }
            }
            if(FeatureSettings.enabled(context,FeatureSettings.INVENTORY) &&
                new File(folder,"job_site_materials.csv").isFile()){
                for(InventoryLayers.SiteEntry site:new InventoryLayers(store).siteMaterials(job)){
                    terms.add(site.name);terms.add(site.unit);terms.add(site.status);
                }
            }
            add(found,query,"JOB",job.id,job.title,
                "Job · "+(customer==null?"Unknown customer":customer.displayName())+
                    " · "+job.date+" · "+job.status,combined(terms));
        }
        if(FeatureSettings.enabled(context,FeatureSettings.CATALOG) &&
            new File(store.root(),"master_data/pricebook.csv").isFile()){
            for(TradeModules.CatalogItem item:new TradeModules(store).catalog()){
                add(found,query,"CATALOG",item.id,item.name,
                    "Catalog · "+item.category+" · $"+item.price(),
                    item.id,item.name,item.category,item.unit,item.supplier);
            }
        }
        if(FeatureSettings.enabled(context,FeatureSettings.INVENTORY)){
            InventoryLayers inventory=new InventoryLayers(store);
            if(new File(store.root(),"master_data/inventory_materials.csv").isFile()){
                for(InventoryLayers.Material stock:inventory.companyMaterials())
                    add(found,query,"INVENTORY",stock.id,stock.name,
                        "Company stock · "+stock.onHand+" "+stock.unit,
                        stock.name,stock.unit,stock.catalogId);
            }
            if(new File(store.root(),"master_data/inventory_tools.csv").isFile()){
                for(InventoryLayers.Tool tool:inventory.tools())
                    add(found,query,"TOOL",tool.id,tool.name,
                        "Equipment · "+tool.status,
                        tool.name,tool.assetTag,tool.jobId,tool.status);
            }
        }
        found.sort(Comparator.comparingInt((Match m)->m.score).reversed()
            .thenComparing(m->m.kind).thenComparing(m->m.title));
        return found.size()>80?new ArrayList<>(found.subList(0,80)):found;
    }
}
