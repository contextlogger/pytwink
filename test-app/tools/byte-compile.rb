require 'efileutils1'
include EFileUtils1
fu_modify_options({nil => {:verbose => true,
                      :noop => $noop}})

# Compiles the specified file to .pyc.
# A Python source file called ``py_file`` must exist.
def compile(py_file)
  py_file =~ /\.py$/ or raise
  base = $`
  pyo_file = base + '.pyo'
  pyc_file = base + '.pyc'

  # To build python2.2 from source
  #   ./configure --prefix=$HOME/local --program-suffix=2.2
  #   make
  #   make install
  #   rm $HOME/local/bin/python
  command = format('python2.2 -OO -c \'%s\'',
    format('import py_compile; py_compile.compile("%s")', py_file))
  sh(command)

  # Not sure if .pyo files are recognized, so let's rename as .pyc.
  mv(pyo_file, pyc_file)
end

for file in ARGV
  compile file
end
