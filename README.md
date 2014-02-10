#hyperion
This provides modern LaTeX classes, workflow information and useful utilities.

##Features
All classes provide the following features:
 - Layout defaults: one-side, A4, 11pt
 - Language: English
 - Fonts: Linux Libertine, microtype, better numbers, units
 - Colors: black hrefs, 4 contrast colors
 - Symbols: math, creative commons
 - Bibliography: biblatex, biber, alphabetic style, URLs
 - Graphics: subfigures, tikz
 - Structure: better table layout, algorithm2e, theorems, definitions
 - Lists: algorithms, symbols

##Compilation
To create the class file, simply run the following command:

    lualatex -pdf hyperion.ins

If you also need a documentation for the class files, just build it by using latexmk:

    latexmk -pdf -lualatex hyperion.dtx

##Usage
The classes are designed to compiled by [lualatex](http://www.luatex.org/). I strongly recommend to use a compilation helper like [latexmk](http://www.ctan.org/pkg/latexmk/). The code is tested using [TeX Live 2013](https://www.tug.org/texlive/), but should also work with newer package versions.

