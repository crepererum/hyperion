#hyperion - classes
This is the core part of the hyperion project, the actual LaTeX classes.

##Compilation
To create the class file, simply run the following command:

    lualatex -pdf hyperion.ins

If you also need a documentation for the class files, just build it by using latexmk:

    latexmk -pdf -lualatex hyperion.dtx

##Usage
The classes are designed to compiled by [lualatex](http://www.luatex.org/). I strongly recommend to use a compilation helper like [latexmk](http://www.ctan.org/pkg/latexmk/). The code is tested using [TeX Live 2013](https://www.tug.org/texlive/), but should also work with newer package versions.

