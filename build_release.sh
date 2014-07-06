#!/usr/bin/env sh

die() {
    printf "FAILED\n"
    exit 1
}

ok() {
    printf "OK\n"
}

base=$(pwd)
printf "Source directory: $base\n"

releasedir=$(mktemp -d)
printf "Release directory: $releasedir\n"

targetdir=$releasedir/hyperion
mkdir -p $targetdir
printf "Uncompressed content: $targetdir\n"

tmpdir=$(mktemp -d)
printf "Temporary directory: $tmpdir\n"


printf "\n== autotex ==\n"

printf "Setup pyvenv..."
penvdir=$tmpdir/penv
pyvenv $penvdir > /dev/null || die
source $penvdir/bin/activate || die
pip install -r $base/autotex/requirements.txt > /dev/null || die
ok

printf "Copy files..."
autotexdir=$targetdir/autotex
autotex=$autotexdir/autotex
mkdir -p $autotexdir
cp $base/autotex/{autotex,README.md,requirements.txt} $autotexdir || die
ok


printf "\n== classes ==\n"

printf "Generate class files..."
classesbuilddir=$tmpdir/classes
mkdir -p $classesbuilddir
cp $base/classes/hyperion.{dtx,ins} $classesbuilddir
cd $classesbuilddir
luatex -pdf hyperion.ins > /dev/null || die
ok

printf "Compile documentation..."
$autotex hyperion.dtx > /dev/null || die
ok

printf "Copy files..."
classesdir=$targetdir/classes
mkdir -p $classesdir
cp hyperion.pdf hyperionartcl.cls hyperionbook.cls hyperiondoc.cls hyperionstandalone.cls $classesdir || die
ok


printf "\n== unicode ==\n"

printf "Download files..."
unicodebuilddir=$tmpdir/unicode
mkdir -p $unicodebuilddir
cp $base/unicode/generate.py $unicodebuilddir
cd $unicodebuilddir
curl -so Blocks.txt "http://www.unicode.org/Public/UCD/latest/ucd/Blocks.txt" > /dev/null || die
curl -so UnicodeData.txt "http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt" > /dev/null || die
ok

printf "Generate package files..."
./generate.py > /dev/null || die
ok

printf "Copy files..."
unicodedir=$targetdir/unicode
mkdir -p $unicodedir
cp out/*.sty $unicodedir || die
ok


printf "\n== random ==\n"

printf "Copy files..."
randomdir=$targetdir/random
mkdir -p $randomdir
cp $base/random/{bibtex.js,publish.sh} $randomdir || die
ok


printf "\n== archives ==\n"
cd $releasedir

printf "zip..."
zip -r hyperion.zip hyperion > /dev/null || die
ok

printf "tar.gz..."
tar -pczf hyperion.tar.gz hyperion > /dev/null || die
ok

printf "\n== clean up ==\n"
deactivate
rm -rf $tmpdir
ok

