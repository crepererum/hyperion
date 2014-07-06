#!/usr/bin/env sh

# check requirements
if ! type gs &> /dev/null; then
    echo "Ghostscript (gs) is required but was not found!"
    exit 1
fi

# check command line arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 file.pdf" >&2
    exit 1
fi

# request more user infos
echo " === Metadata === "
read -p "Title: " title
read -p "Author: " author
read -p "Subject: " subject
read -p "Keywords: " keywords
echo ""

# setup
input=$1
name=$(basename $1 .pdf)
output="$name.publish.pdf"
tmpdir=$(mktemp -d)
pdfmarks="$tmpdir/pdfmarks"
date=$(date +"%Y%m%d%H%M%S")

# write pdfmarks file
cat > $pdfmarks <<EOF
[ /Title ($title)
  /Author ($author)
  /Subject ($subject)
  /Keywords ($keywords)
  /ModDate (D:$date)
  /CreationDate (D:$date)
  /Creator (hyperion)
  /Producer (hyperion)
  /DOCINFO pdfmark
EOF

# run ghostscript
printf "Processing file..."
gs -q -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress -dCompressFonts=true -dEmbedAllFonts=true -dNOPAUSE -dBATCH -sOutputFile=$output $input $pdfmarks
echo "done"

# clean up
rm -rf $tmpdir

