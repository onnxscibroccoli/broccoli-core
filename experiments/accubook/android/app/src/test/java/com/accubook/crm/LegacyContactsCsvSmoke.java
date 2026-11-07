package com.accubook.crm;

import java.io.IOException;

/** CSV importer never writes workspace data; commit is a separate user action. */
public final class LegacyContactsCsvSmoke {
    private static void ok(boolean b,String error){if(!b)throw new AssertionError(error);}
    private static void fail(String csv) throws Exception {
        boolean rejected=false;
        try{LegacyContactsCsv.parse(csv);}
        catch(IOException expected){rejected=true;}
        ok(rejected,"Malformed CRM CSV accepted");
    }
    public static void main(String[] args) throws Exception {
        String csv="Contact Name,Work Phone,E-mail,Notes\r\n"
            +"\"Sam, Jr\",555-0100,sam@example.invalid,Need gutters\r\n"
            +"Mia,555-0199,mia@example.invalid,Roofing\r\n"
            +",,no-name@example.invalid,Unknown\r\n";
        LegacyContactsCsv source=LegacyContactsCsv.parse(csv);
        ok(source.count()==3,"Wrong source row count");
        ok(source.guess("name")==0,"Contact Name not recognized");
        ok(source.guess("phone")==-1,"Unexpected ambiguous Work Phone guess");
        ok(source.guess("email")==2,"E-mail header not recognized");
        LegacyContactsCsv.Preview preview=source.preview(0,1,2);
        ok(preview.sourceRows==3 && preview.entries.size()==2 && preview.skipped==1,
            "Unnamed source must be shown as skipped, not imported");
        ok(preview.entries.get(0).name.equals("Sam, Jr"),
            "RFC 4180 quoted name lost");
        ok(preview.entries.get(0).source.startsWith("csv:"),
            "Source fingerprint missing");
        ok(preview.entries.get(0).source.equals(
            LegacyContactsCsv.parse(csv).preview(0,1,2).entries.get(0).source),
            "Same file must generate stable reimport IDs");
        boolean dup=false;
        try{source.preview(0,0,2);}
        catch(IOException expected){dup=true;}
        ok(dup,"One column mapped twice");
        boolean badName=false;
        try{source.preview(-1,1,2);}
        catch(IOException expected){badName=true;}
        ok(badName,"Name mapping was optional");
        fail("Email,Email\r\na@b.invalid,a@b.invalid\r\n");
        fail("Name,Phone\r\nAmy\r\n");
        fail("Name,Phone\r\n\"unterminated,123\r\n");
        fail("Name\r\n");
        boolean longName=false;
        try{LegacyContactsCsv.parse("Name\r\n"+"X".repeat(181)+"\r\n").preview(0,-1,-1);}
        catch(IOException expected){longName=true;}
        ok(longName,"Overlong value was imported");
        ok(LegacyContactsCsv.parse("Name,Phone,Mobile\r\nA,1,2\r\n")
            .guess("phone")==-1,"Ambiguous phone columns must be manually mapped");
        System.out.println("LegacyContactsCsvSmoke: PASS");
    }
}
