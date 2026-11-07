package com.accubook.crm;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/**
 * Offline help library. Every article has a one-sentence answer,
 * step-by-step instructions, a note about limitations and search terms.
 */
public final class HelpTopics {
    private HelpTopics(){}
    public static final class Topic {
        public final String title,quick,steps,search;
        Topic(String title,String quick,String steps,String synonyms){
            this.title=title;this.quick=quick;this.steps=steps;
            this.search=(title+" "+quick+" "+steps+" "+synonyms).toLowerCase(Locale.ROOT);
        }
        public String full(){return quick+"\n\n"+steps;}
    }
    public static List<Topic> all(){
        return Arrays.asList(
            new Topic("Start with one customer and one job",
                "Add a customer, create a job, and do the work. Everything else is optional.",
                "1. Open Customers → New customer.\n2. Add the name and save.\n"+
                "3. Open that customer → New job.\n4. Open the job. Switch between Photos, "+
                "Notes, Money and Schedule at the top.\n5. Record work, then print an estimate or invoice.",
                "getting started onboarding first"),
            new Topic("Contacts are not customers",
                "Import every phone contact without automatically making customers.",
                "Open Contacts → Import all (or choose contacts). Find someone by name or number. "+
                "Only promote a contact when they actually become a customer.",
                "phone address book bulk import"),
            new Topic("Find a job quickly",
                "Open Home → Find anything. One box finds existing records.",
                "Search by customer/contact name, phone, address, invoice reference, note, "+
                "material, job ID or value in a custom field. Search runs locally only "+
                "when you tap Search; narrow long result lists with more terms.",
                "search lookup address phone work order invoice vin"),
            new Topic("Take and reorder photos",
                "Open a job → Photos → Import multiple photos.",
                "Tap a photo for a preview. Long-press or use the three-dot action to move "+
                "it up, move it down, or remove it. Backup preserves the photo order.",
                "camera images attachments gallery sort pictures"),
            new Topic("Type notes without a mandatory drop-down",
                "Open a job → Notes. Type exactly what happened.",
                "For billable work open Money → Add labor, material or discount. "+
                "Type the description; local pricebook matches appear as optional suggestions. "+
                "Tap one to fill its rate, or ignore suggestions and enter your own price. "+
                "Nothing is billed until you save the line.",
                "free text invoice pricebook auto fill cost crew field"),
            new Topic("Use a simple invoice",
                "Open a job → Money → Preview / edit invoice.",
                "Add a line, quantity and unit rate. Preview the document; print or save to PDF "+
                "using Android's print destination. Recording a payment is separate from invoicing.",
                "flyer slip printed bill quote estimate receipt"),
            new Topic("Change the work after an estimate",
                "Use a linked change order, not another unrelated quote.",
                "Open the job → Money → New change order. Add work lines and show the total "+
                "difference. The customer reviews and signs on the device. "+
                "Only then tap Add to invoice. Stable line references prevent the same "+
                "change-order line from being added twice on retry.",
                "change order variations supplement acknowledgement signature"),
            new Topic("Understand the signature",
                "Finger or stylus signatures are recorded locally as PNG with time and hashes.",
                "An acknowledged change order becomes read-only. The app checks the signed "+
                "content and signature hash before billing. This detects changes but does "+
                "not independently verify the signer's identity or provide a certificate.",
                "sign approval legal tamper evidence"),
            new Topic("Record money without exporting everything",
                "Quick PDF and Custom CSV ZIP are separate report types.",
                "Open Business → Reports. Select the sections, individual payment methods "+
                "and expense categories to include. Cash and Cash App are optional. "+
                "Nothing uploads automatically. Inspect CSV before importing to accounting software.",
                "reports quickbooks zip cash cash app accounting privacy ledgers export"),
            new Topic("Hide modules you do not use",
                "Start simple. Switch on additional tools only when useful.",
                "Open Business → Settings → Modules. Turn on crew, catalog, worker time, "+
                "GPS, repeat-service due dates or experimental calendar sync. Switching off "+
                "a module "+
                "hides its controls and never deletes stored records.",
                "solo business feature flags crew toggles preferences"),
            new Topic("Customize a job template",
                "The owner can change fields and order without outside approval.",
                "Open the master checklist from Home, or open a job → Checklist. "+
                "Use a three-dot menu or long-press for edit, move up/down, required or remove. "+
                "Existing job answers are not silently overwritten by master edits.",
                "master fields checklists reorder remove required trade"),
            new Topic("Set a company color or logo",
                "Choose colors visually and import a business logo from the device.",
                "Open Business → Edit company or Choose business logo. Existing brand "+
                "data is kept until you explicitly change it. Job colors are set in "+
                "Schedule and customer colors in their contact preferences.",
                "branding rainbow logo color colors picker"),
            new Topic("Make reminders without cloud sync",
                "Local dumpster pickup alerts work without a hosted calendar.",
                "Open the job → Materials → Schedule device-only pickup alert. "+
                "For an Android Calendar event, use Add to Calendar. "+
                "External calendar account synchronization is optional and experimental.",
                "due dates dumpster local alarm calendar reminders"),
            new Topic("Keep a simple material and tool inventory",
                "Turn on just the inventory you use. Nothing is automatically billed.",
                "Open Business → Settings and enable Company materials, job-site stock "+
                "and tools. Then open Business → Company materials + tool inventory. "+
                "Add stock with a name, unit, counted quantity and cost; or copy a "+
                "pricebook item. Add tools with an optional identifying tag. "+
                "Open a job → Materials to record Delivered, Used or Returned items "+
                "and check out an available tool. Return a tool from the job or "+
                "Business inventory. All records are local and included in backup. "+
                "Job-site observations do not silently reduce company counts, "+
                "create expenses or add invoice lines. Update stock manually.",
                "inventory counts stock supplies equipment checkout returned tools "+
                "materials deliveries ledger offline"),
            new Topic("Know who needs repeat service",
                "Repeat service is an optional due-by-date and mileage list.",
                "Enable Repeat-service due dates in Business → Settings. Open an old "+
                "job → Overview → Set next service due. Enter when the service "+
                "actually happened and the months or miles until it is due again. "+
                "Home shows date-due reminders. You can save printable PDF slips, "+
                "pause rules and update completion dates. It never contacts customers "+
                "or creates new jobs by itself.",
                "oil change mileage gutters recurring service reminder slips"),
            new Topic("Keep a safe backup",
                "Export an encrypted backup before restoring or uninstalling.",
                "From Home choose Create encrypted workspace backup, set a strong password "+
                "and save outside the app's private storage. Verify the saved file. "+
                "Restore validates CSV relationships and signed change-order evidence "+
                "before replacing records. Uninstalling removes the active workspace.",
                "backup recovery restore zip private security encryption"),
            new Topic("Accessibility and large text",
                "The visual app works with touch; labeled actions support assistive technology.",
                "Open Settings → Android accessibility settings to turn on TalkBack. "+
                "Three-dot menus also expose actions available on long-press. "+
                "Comprehensive device-based TalkBack testing is still pending.",
                "screenreader screen reader keyboard voice low vision"),
            new Topic("Features still in development",
                "A planned feature is not a working feature.",
                "Automatic repeat-job creation, persistent full-text indexing, multi-property "+
                "records, inventory reconciliation, supplier ordering, deep AR/AP/GL "+
                "posting and full QuickBooks mappings are not complete. "+
                "The app continues to operate offline without these.",
                "roadmap future production not ready inventory vehicles recurring")
        );
    }
    public static List<Topic> search(String query){
        String q=query==null?"":query.toLowerCase(Locale.ROOT).trim();
        List<Topic> matches=new ArrayList<>();
        for(Topic topic:all()){
            boolean found=q.isEmpty();
            for(String token:q.split("\\s+"))if(!token.isEmpty() && topic.search.contains(token))
                found=true;
            if(found)matches.add(topic);
        }
        return matches;
    }
}
