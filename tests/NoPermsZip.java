import java.io.*;
import java.util.zip.*;
public class NoPermsZip
{
   public static void main(String[] args) throws Exception
   {
      ZipOutputStream out = new ZipOutputStream(new FileOutputStream("no_perms.zip"));
      FileInputStream in = new FileInputStream("./test_run.sh");
      int abyte;
      out.putNextEntry(new ZipEntry("./test_run.sh"));
      try
      {
         while ((abyte = in.read()) != -1)
         {
            out.write(abyte);
         }
      }
      finally
      {
         in.close();
      }
      out.closeEntry();
      out.close();
   }
}
