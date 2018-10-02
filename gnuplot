set encoding utf8

# line styles for ColorBrewer Set1
# for use with qualitative/categorical data
# provides 8 easy-to-name colors
# compatible with gnuplot >=4.2
# author: Anna Schneider

# line styles
set style line 1 lt 1 lw 2 lc rgb '#E41A1C' # red
set style line 2 lt 1 lw 2 lc rgb '#377EB8' # blue
set style line 3 lt 1 lw 2 lc rgb '#4DAF4A' # green
set style line 4 lt 1 lw 2 lc rgb '#984EA3' # purple
set style line 5 lt 1 lw 2 lc rgb '#FF7F00' # orange
set style line 6 lt 1 lw 2 lc rgb '#FFFF33' # yellow
set style line 7 lt 1 lw 2 lc rgb '#A65628' # brown
set style line 8 lt 1 lw 2 lc rgb '#F781BF' # pink

# palette
set palette maxcolors 8
set palette defined ( 0 '#E41A1C',\
											1 '#377EB8',\
											2 '#4DAF4A',\
											3 '#984EA3',\
											4 '#FF7F00',\
											5 '#FFFF33',\
											6 '#A65628',\
											7 '#F781BF' )

# Standard border
set style line 11 lc rgb '#808080' lt 1 lw 3
set border 0 back ls 11
set tics out nomirror

# Standard grid
set style line 12 lc rgb '#808080' lt 0 lw 1
set grid back ls 12
unset grid
