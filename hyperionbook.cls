\NeedsTeXFormat{LaTeX2e} % We do need LaTeX2e
\ProvidesClass{hyperionbook}
\LoadClass[% Class based on scrbook
    fontsize=11pt,% bigger font
    paper=a4,% paper size
    pagesize,% set pagesize in PDF
    twoside=false,% =oneside
    listof=totoc,%add list of figures to toc
    draft% TODO remove this!
]{scrbook}

%---------------------------------------
%---------REQUIREMENTS------------------
%---------------------------------------
\RequirePackage{ifluatex}
\ifluatex
\else
\ClassError{hyperionbook}{lualatex required!}{Please use lualatex to compile this file. See http://www.luatex.org/}
\fi

%---------------------------------------
%---------PACKAGES----------------------
%---------------------------------------

%---language--------
\RequirePackage[english]{babel}

%---font config-----
\RequirePackage[T1]{fontenc}
\RequirePackage{libertine}
\RequirePackage{ccicons}

%---microtype-------
\RequirePackage[
    activate={true,nocompatibility},% activate protrusion and expansion
    final,% enable microtype; use "draft" to disable
    tracking=true,% activate these techniques
%    kerning=true,% -''-
%    spacing=basictext,% activate and supress warning
    factor=1100,% add 10% to the protrusion amount (default is 1000)
    stretch=10,% reduce stretchability/shrinkability (default is 20/20)
    shrink=10% -''-
]{microtype}
\microtypecontext{spacing=nonfrench}

%---links-----------
\RequirePackage{hyperref}

%---math------------
\RequirePackage{amsmath}
\RequirePackage{amssymb}

%---theorems--------
\RequirePackage{amsthm}

%---nice table rules
\RequirePackage{booktabs}

%---color-----------
% before: tikz
\PassOptionsToPackage{table}{xcolor}

%---graphics--------
\PassOptionsToPackage{
    final% ignore draft option
}{graphicx}
\RequirePackage{tikz}
\RequirePackage{tikz-3dplot}
\RequirePackage{pgfplots}

%---csquotes--------
% before: bibtex
\RequirePackage{csquotes}

%---bibtex----------
% after: hyperref
\RequirePackage[
    backend=biber,% nice fast backend
    style=alphabetic% how the shortcuts should look like
]{biblatex}

%---units-----------
% after: amssymb
\RequirePackage{siunitx}

%---subfigures------
\RequirePackage[
    list=on% add subfigures/-tables to list of figures
]{subcaption}

%---list of symbols-
\RequirePackage[intoc]{nomencl}

%---list of everything
\RequirePackage{tocbibind}

%---algorithm-------
\RequirePackage[
    ruled,% nice lines above/beyond the algorithms
    linesnumbered% draw line numbers
]{algorithm2e}

%---better tables---
\RequirePackage{tabularx}

%---urls------------
\RequirePackage{url}

%---blindtext-------
\RequirePackage{blindtext}


%---------------------------------------
%---------SETTINGS----------------------
%---------------------------------------

% path of images
\graphicspath{{./img/}}

% color
\definecolor{colcontrast}{RGB}{40,100,40}
\definecolor{colcontrast2}{RGB}{40,40,100}
\definecolor{colcontrast3}{RGB}{80,20,80}
\definecolor{colcontrast4}{RGB}{80,80,20}

% links
\hypersetup{
    colorlinks,% colored text instead of borders
    linkcolor=black,% black inter document links
    urlcolor=black,% black urls
    citecolor=black,% black cite
    final% also work in draft mode, TODO remove this!
}

% tikz libs
\usetikzlibrary{
    arrows,
    backgrounds,
    positioning
}

% pgfplots
\pgfplotsset{
    compat=newest,
    compat/show suggested version=false
}

% tikz macros
\tikzset{
% scaling of plot marks (true/false):
    scale plot marks/.is choice,
    scale plot marks/false/.code={
        \def\pgfuseplotmark##1{\pgftransformresetnontranslations\csname pgf@plot@mark@##1\endcsname}
    },
    scale plot marks/true/.style={},
    scale plot marks/.default=true,
%
% arrow styles:
    >=stealth',
    axis/.style={->, very thick, >=stealth'},
%
% graphs and flowcharts:
    graphedge/.style={ultra thick},
    graphnode/.style={circle, draw, fill=white},
    blocknode/.style={draw, fill=white, minimum width=4em},
%
% different dots and lines used by diagrams:
    dot/.style={mark=*, mark size=0.08em, only marks, scale plot marks=false},
    measure/.style={mark=*, mark size=0.12em, smooth, scale plot marks=false}
}

% circled characters (e.g. copyright symbol)
\newcommand*\circled[1]{\tikz[baseline={($(char.south) + (0,0.5pt)$)}]{
    \node[shape=circle,draw,inner sep=0.5pt,font=\tiny,thick] (char) {\textsf{#1}};}}

% filled quad (used for graphics)
\def\filledquad#1#2{
\begin{scope}[shift={#1}]
    \draw [fill=black](0,0) -- (#2,0) -- (#2,#2) -- (0,#2) -- cycle;
\end{scope}
}

% bibtex
\addbibresource{citiation.bib}

% list of symbols
\makenomenclature
\renewcommand{\nomname}{List of Symbols}

% list of algorithms
\newcommand{\listofalgorithmes}{\tocfile{\listalgorithmcfname}{loa}}

% math macros
\newcommand{\set}[1]{\mathbb{#1}}
\newcommand{\card}[1]{\left|#1\right|}
\newcommand{\concat}{+\kern-0.8ex:}
\newcommand{\prob}[1]{\mathbb{P}\left(#1\right)}
\newcommand{\mutual}[2]{\mathrm{I}\left(#1,#2\right)}
\newcommand{\entropy}[1]{\mathrm{H}\left(#1\right)}
\newcommand{\code}[1]{\texttt{#1}}

% calculation helper
\newcommand{\mycalc}[2]{
    \pgfkeys{/pgf/fpu, /pgf/fpu/output format=fixed}
    \pgfmathparse{#2}
    \edef#1{\pgfmathresult}
    \pgfkeys{/pgf/fpu=false}
}

% theorems, defs, ...
\theoremstyle{plain}
\newtheorem{envtheo}{Theorem}
\theoremstyle{definition}
\newtheorem{envdef}{Definition}

% table stuff
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}
\newcommand*\rot{\rotatebox{90}}

%% **** END OF CLASS ****

