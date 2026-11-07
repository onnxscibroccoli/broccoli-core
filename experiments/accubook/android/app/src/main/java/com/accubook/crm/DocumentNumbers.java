package com.accubook.crm;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Stable customer-facing reference that never exposes the raw internal job UUID. */
public final class DocumentNumbers {
    private static final String ALPHABET="0123456789ABCDEFGHJKMNPQRSTVWXYZ";
    private DocumentNumbers(){}
    public static String reference(String jobId,String scheduledDate,boolean estimate){
        if(jobId==null||!jobId.matches("JOB-[0-9a-f]{32}"))
            throw new IllegalArgumentException("Invalid internal job reference");
        // Rescheduling must never change a customer-facing document reference.
        byte[] digest;
        try{
            digest=MessageDigest.getInstance("SHA-256")
                .digest(jobId.getBytes(StandardCharsets.US_ASCII));
        }catch(NoSuchAlgorithmException impossible){
            throw new IllegalStateException("SHA-256 missing",impossible);
        }
        StringBuilder code=new StringBuilder(12);
        int buffer=0,bits=0;
        for(byte b:digest){
            buffer=(buffer<<8)|(b&0xff);
            bits+=8;
            while(bits>=5&&code.length()<12){
                bits-=5;
                code.append(ALPHABET.charAt((buffer>>bits)&31));
            }
            if(code.length()==12)break;
        }
        return (estimate?"EST-":"INV-")+code.substring(0,4)+"-"+
            code.substring(4,8)+"-"+code.substring(8,12);
    }
}
