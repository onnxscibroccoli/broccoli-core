package com.accubook.crm;

import android.content.Context;
import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** Atomic, portable workspace settings; no cloud, external storage or account. */
public final class BusinessSetupStore {
    public static final String PATH="templates/business_setup.csv";
    private static final int MAX_BYTES=4096;
    private BusinessSetupStore(){}

    private static File target(Context context) {
        return new File(new File(context.getFilesDir(),"Accubook Workspace"),PATH);
    }
    public static boolean exists(Context context) {
        File file=target(context);
        return file.isFile()||new File(file.getPath()+".bak").isFile();
    }
    public static BusinessSetupProfile load(Context context) throws IOException {
        if(!exists(context)) return null;
        AtomicFile file=new AtomicFile(target(context));
        try(InputStream in=file.openRead();ByteArrayOutputStream output=new ByteArrayOutputStream()){
            byte[] buffer=new byte[1024];
            int size;
            while((size=in.read(buffer))!=-1){
                if(output.size()+size>MAX_BYTES)throw new IOException("Business setup file exceeds limit");
                output.write(buffer,0,size);
            }
            return BusinessSetupProfile.fromCsv(output.toString(StandardCharsets.UTF_8.name()));
        }
    }
    public static void save(Context context,BusinessSetupProfile profile) throws IOException {
        File dest=target(context);
        File folder=dest.getParentFile();
        if(!folder.isDirectory()&&!folder.mkdirs())throw new IOException("Cannot create settings folder");
        byte[] bytes=profile.toCsv().getBytes(StandardCharsets.UTF_8);
        if(bytes.length>MAX_BYTES)throw new IOException("Business setup file exceeds limit");
        AtomicFile file=new AtomicFile(dest);
        FileOutputStream out=null;
        try{
            out=file.startWrite();
            out.write(bytes);
            file.finishWrite(out);
        }catch(IOException|RuntimeException error){
            if(out!=null)file.failWrite(out);
            throw error;
        }
    }
}
