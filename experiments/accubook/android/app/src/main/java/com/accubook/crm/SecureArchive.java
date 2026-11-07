package com.accubook.crm;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.CipherInputStream;
import javax.crypto.CipherOutputStream;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Password-encrypted, authenticated, portable backup container.
 * IMPORTANT: Encrypts exported backup, NOT the active plaintext workspace.
 * No remote services; the passphrase is not saved.
 */
public final class SecureArchive {
    private SecureArchive() {}
    private static final byte[] MAGIC={'A','C','B','K','2'};
    private static final int SALT=16,NONCE=12,ITERATIONS=210_000;
    public static final long MAX_CLEARTEXT=512L*1024*1024;

    private static SecretKeySpec key(char[] password,byte[] salt)
        throws GeneralSecurityException {
        if(password==null||password.length<12||password.length>512)
            throw new IllegalArgumentException("Use a passphrase of 12–512 characters");
        PBEKeySpec parameters=new PBEKeySpec(password,salt,ITERATIONS,256);
        try {
            byte[] bits=SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                .generateSecret(parameters).getEncoded();
            try{return new SecretKeySpec(bits,"AES");}
            finally{Arrays.fill(bits,(byte)0);}
        }finally{parameters.clearPassword();}
    }
    public static OutputStream encryptStream(OutputStream destination,char[] passphrase)
        throws IOException {
        if(destination==null)throw new IOException("Missing encrypted backup destination");
        byte[] salt=new byte[SALT],nonce=new byte[NONCE];
        SecureRandom random=new SecureRandom();
        random.nextBytes(salt);random.nextBytes(nonce);
        try{
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key(passphrase,salt),
                new GCMParameterSpec(128,nonce));
            cipher.updateAAD(MAGIC);
            destination.write(MAGIC);
            destination.write(salt);
            destination.write(nonce);
            // Caller MUST close this stream to append authenticated GCM tag.
            return new CipherOutputStream(destination,cipher);
        }catch(GeneralSecurityException error){
            throw new IOException("Cannot initialize encrypted archive",error);
        }
    }
    public static File decryptToTemp(InputStream input,File privateDirectory,char[] passphrase)
        throws IOException {
        if(input==null||privateDirectory==null)
            throw new IOException("No encrypted archive selected");
        byte[] header=new byte[MAGIC.length+SALT+NONCE];
        int offset=0;
        while(offset<header.length){
            int n=input.read(header,offset,header.length-offset);
            if(n<0)throw new IOException("Truncated encrypted archive");
            offset+=n;
        }
        for(int i=0;i<MAGIC.length;i++)
            if(header[i]!=MAGIC[i])throw new IOException("Not an Accubook ACBK2 encrypted backup");
        byte[] salt=Arrays.copyOfRange(header,MAGIC.length,MAGIC.length+SALT);
        byte[] nonce=Arrays.copyOfRange(header,MAGIC.length+SALT,header.length);
        File temporary=null;
        boolean authenticated=false;
        try {
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(passphrase,salt),
                new GCMParameterSpec(128,nonce));
            cipher.updateAAD(MAGIC);
            temporary=File.createTempFile("accubook-decrypt-", ".zip",privateDirectory);
            long total=0;
            try(CipherInputStream encrypted=new CipherInputStream(input,cipher);
                FileOutputStream output=new FileOutputStream(temporary)){
                byte[] buffer=new byte[8192];
                int count;
                // Drain all the way through GCM tag BEFORE workspace restore.
                while((count=encrypted.read(buffer))!=-1){
                    total+=count;
                    if(total>MAX_CLEARTEXT)throw new IOException("Encrypted archive too large");
                    output.write(buffer,0,count);
                }
                output.getFD().sync();
            }
            authenticated=true;
            return temporary;
        }catch(GeneralSecurityException error){
            throw new IOException("Encrypted backup could not be unlocked",error);
        }catch(IOException error){
            throw new IOException("Wrong passphrase, corrupted backup, or failed write: "
                +error.getMessage(),error);
        }finally{
            if(!authenticated&&temporary!=null)temporary.delete();
        }
    }
    /**
     * Decrypt, authenticate completely, then invoke existing staged ZIP restore.
     * Plaintext temporary file exists briefly in private cache and is deleted.
     */
    public static void restore(WorkspaceStore store,InputStream input,
                               File privateCache,char[] passphrase) throws IOException {
        File copy=null;
        try{
            copy=decryptToTemp(input,privateCache,passphrase);
            try(InputStream zip=new FileInputStream(copy)){
                store.restoreBackup(zip);
            }
        }finally{
            if(copy!=null&&!copy.delete()&&copy.exists())
                throw new IOException("Sensitive decrypted temporary file needs cleanup");
        }
    }
}
