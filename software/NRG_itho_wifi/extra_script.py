Import("env", "projenv")
import gzip, os, glob, shutil, json

from SCons.Script import (
    ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild, Builder, Default,
    DefaultEnvironment)

from sys import platform

fwversion = 'undefined'
hwversion = 'undefined'
release   = 'undefined'
hwrev     = 'undefined'

my_flags = env.ParseFlags(env['BUILD_FLAGS'])
#print(my_flags)

defines = my_flags.get("CPPDEFINES")
for i in defines:
   if (i[0] == 'VERSION'):
      fwversion = i[1]
      print ('\nFirmware version: ' + i[1])
   if (i == 'NON_CVE'):
      hwversion = 'NON_CVE'
   if (i == 'CVE'):
      hwversion = 'CVE'
   if (i == 'BETA'):
      release = 'beta'
   if (i == 'STABLE'):
      release = 'stable'      

print ('Hardware version: ' + hwversion)
print ("\n")

PIOENV = env.subst("$PIOENV")
PROGNAME = env.subst("$PROGNAME")
firmware_bin = PROGNAME + ".bin"
PROJECT_DIR = env.subst("$PROJECT_DIR")
PROJECT_WORKSPACE_DIR = env.subst("$PROJECT_WORKSPACE_DIR")
PROJECT_BUILD_DIR = env.subst("$PROJECT_BUILD_DIR")
PROJECT_SRC_DIR = env.subst("$PROJECT_SRC_DIR")

print('PIOENV:' + PIOENV)
print('PROJECT_BUILD_DIR:' + PROJECT_BUILD_DIR)
print('PROJECT_DIR:' + PROJECT_DIR)
#print('PROGNAME:' + PROGNAME)
print('PROJECT_SRC_DIR:' + PROJECT_SRC_DIR)

if platform == "linux":
   print('Detected platform: Linux')
   DIR_SEPERATOR = '/'
elif platform == "darwin":
   print('Detected platform: MacOS')
   DIR_SEPERATOR = '/'
elif platform == "win32":
   print('Detected platform: Windows')
   DIR_SEPERATOR = '\\'
else:
   print('Detected platform: Failed!')
   exit()

WEBROOT_SRC_DIR = PROJECT_SRC_DIR + DIR_SEPERATOR + 'webroot_source' + DIR_SEPERATOR
CONTROLS_JS_SRC_DIR = WEBROOT_SRC_DIR + 'controls_js_sources' + DIR_SEPERATOR
WEBROOT_OUT_DIR = PROJECT_SRC_DIR + DIR_SEPERATOR + 'webroot' + DIR_SEPERATOR
PROJECT_BIN_DIR = PROJECT_BUILD_DIR + DIR_SEPERATOR + PIOENV + DIR_SEPERATOR
PROJECT_COMPILED_DIR = PROJECT_DIR + DIR_SEPERATOR + '..' + DIR_SEPERATOR + '..' + DIR_SEPERATOR + 'compiled_firmware_files' + DIR_SEPERATOR
HW_BIN_DIR = ''

if (PIOENV == 'release_cve' or PIOENV == 'beta_cve') :
   hwrev = '-hw2'
   HW_BIN_DIR = 'hardware_rev_2' + DIR_SEPERATOR
elif (PIOENV == 'release_noncve' or PIOENV == 'beta_noncve') :
   hwrev = '-noncve'
   HW_BIN_DIR = 'non-cve_rev_1' + DIR_SEPERATOR
elif (PIOENV == 'debug') :
   hwrev = '-debug'
   HW_BIN_DIR = 'debug' + DIR_SEPERATOR
else :
   hwrev = '-dev'
   HW_BIN_DIR = 'dev' + DIR_SEPERATOR

def export_version():
   outfile = open(PROJECT_SRC_DIR + DIR_SEPERATOR + "version.h","w", encoding='utf-8')
   outfile.write("#pragma once\n\n#define FWVERSION \"" + fwversion + "\"\n")

def concat_controls_js():
   print('### Combining javascript and HTML files into controls.js...')
   out_filename = WEBROOT_SRC_DIR + 'controls.js'
   js_infile = open(CONTROLS_JS_SRC_DIR + 'javascript.js', "r", encoding='utf-8')
   print('\tAdding: ' + CONTROLS_JS_SRC_DIR + 'javascript.js')
   outfile = open(out_filename, "w", encoding='utf-8')
   outfile.write("//This file is automatically generated - do not edit this file, edit the files in dir controls_js_sources instead and run the build\n")
   outfile.write(js_infile.read())
   for files in glob.glob(CONTROLS_JS_SRC_DIR + '*.html'):
      print('\tAdding: ' + files)
      with open(files, 'r', encoding='utf-8') as infile:
         name , extension = os.path.splitext(os.path.basename(files))
         outfile.write("\nvar " + name + " = `\n")
         outfile.write(infile.read())
         outfile.write("\n`;\n")
         
def pop_first_line(file):
    with open(file, 'r+', encoding='utf-8') as f:
        firstLine = f.readline() # read the first line and throw it out
        data = f.read() # read the rest
        outfile = open(WEBROOT_SRC_DIR + 'controls_temp.js', "w", encoding='utf-8')
        outfile.write(data)


def make_c_header(inName, outName):
   if(inName == 'controls.js'):
      inFileBytes = pop_first_line(WEBROOT_SRC_DIR + 'controls.js')
   else:
      infile = open(WEBROOT_SRC_DIR + inName, "rb")
      inFileBytes = infile.read()
   
   inFileGziped = gzip.compress(inFileBytes)
   print("\twebroot_source" + inName + ' non compressed (' + str(len(inFileBytes)) + " bytes), gziped (" + str(len(inFileGziped)) + " bytes) - writing to: webroot/" + outName + ".h")
   outfile = open(WEBROOT_OUT_DIR + outName + ".h","w") 
      
   outfile.write("#pragma once\n\nconst unsigned char " + outName + "[] = {\n\t\t")
   lineBreak = 40
   for b in inFileGziped:
      outfile.write(hex(b))
      outfile.write(", ")
      if lineBreak == 0:
         outfile.write("\n\t\t")
         lineBreak = 39
      lineBreak-=1
   outfile.write("};\n\nunsigned int " + outName + "_len = " + str(len(inFileGziped)) + ";\n")

   infile.close()
   outfile.close()

def build_webUI(*args, **kwargs):
   print('\n### Building webroot sources...\n')
   concat_controls_js()
   print('### Compressing webroot sources into gzipped header files...')
   pop_first_line(WEBROOT_SRC_DIR + 'controls.js')
   make_c_header("controls_temp.js", "controls_js_gz")
   os.remove(WEBROOT_SRC_DIR + "controls_temp.js")
   make_c_header("index.html", "index_html_gz")
   make_c_header("edit.html", "edit_html_gz")
   make_c_header("pure-min.css", "pure_min_css_gz")
   make_c_header("zepto.min.js", "zepto_min_js_gz")
   make_c_header("favicon.png", "favicon_png_gz")
   print('\n### Webroot sources ready...\n')

def copy_firmware():
   if os.path.isfile(PROJECT_BIN_DIR + firmware_bin):
      print('Coping firmware file to: ' + PROJECT_COMPILED_DIR + HW_BIN_DIR + 'nrgitho' + hwrev + '-v' + fwversion + '.bin\n')      
      shutil.copy(PROJECT_BIN_DIR + firmware_bin, PROJECT_COMPILED_DIR + HW_BIN_DIR + 'nrgitho' + hwrev + '-v' + fwversion + '.bin')
      #check_sha1(name)
   else :
      print('Copy error! firmware file not found')

def update_releaseinfo():
   if(release != 'undefined' and hwversion != 'undefined'):
      print('\n### Updating releaseinfo for the '+ release +' release\n')

      latest_fw_key = "latest_fw" if release == 'stable' else "latest_beta_fw"
      latest_link_key = "link" if release == 'stable' else "link_beta"
      latest_fw_file = 'nrgitho' + hwrev + '-v' + fwversion + '.bin'
      
      releasefile = PROJECT_COMPILED_DIR + "firmware.json"
      f = open(releasefile)
      data = json.load(f)
      f.close()

      if(hwversion == 'CVE'):
         data['hw_rev']['2'][latest_link_key] = 'https://github.com/arjenhiemstra/ithowifi/raw/master/compiled_firmware_files/hardware_rev_2/' + latest_fw_file
         data['hw_rev']['2'][latest_fw_key] = fwversion
      elif(hwversion == 'NON_CVE'):
         data['hw_rev']['NON-CVE 1'][latest_link_key] = 'https://github.com/arjenhiemstra/ithowifi/raw/master/compiled_firmware_files/non-cve_rev_1/' + latest_fw_file
         data['hw_rev']['NON-CVE 1'][latest_fw_key] = fwversion

      json_object = json.dumps(data, indent = 4)

      with open(PROJECT_COMPILED_DIR + "firmware.json", "w", encoding='utf-8') as outfile:
         outfile.write(json_object)      

def build_before(*args, **kwargs):
   print('\n### running pre build commands...\n')
   export_version()
   build_webUI(*args, **kwargs)
   

def build_after(*args, **kwargs):
   print('\n### running post build commands...\n')
   copy_firmware()
   update_releaseinfo()
   

env.Execute(build_before)

env.AddPostAction("buildprog", build_after)

