require 'tempfile'

VERSION = File.open('VERSION') { |fp| fp.read().chomp() }

DIST_DIR = 'dist'
WHEEL_FILE = "#{DIST_DIR}/slyphon_zshhist_backup-#{VERSION}-py3-none-any.whl"
PEX_FILE = "#{DIST_DIR}/zshhist.pex"


directory DIST_DIR

file WHEEL_FILE => DIST_DIR do
  sh "pip3 wheel -w #{DIST_DIR} ."
end

def tempfile(*a)
  t = Tempfile.new(*a)
  begin
    yield t
  ensure
    t.close
  end
end

file PEX_FILE => WHEEL_FILE do
  #pex -r requirements.txt -m slyphon.zshbackup.app:main --python-shebang='/usr/bin/env python3' -o /tmp/zsh-hist-backup.pex --python=python3 -f $PWD -r <(echo 'slyphon-zshhist-backup')

  tempfile('other-reqs') do |tmp|
    tmp.puts('slyphon-zshhist-backup')
    tmp.flush()
    sh "pex -r requirements.txt -s slyphon.zshbackup.app -e slyphon.zshbackup.app:main --python-shebang='/usr/bin/env python3' -o #{PEX_FILE} --python=python3 -f #{DIST_DIR} -r #{tmp.path}"
  end
end

CLEANUP = FileList[WHEEL_FILE, PEX_FILE]

task :build => PEX_FILE

task :clean do
  rm_rf CLEANUP
end

task :run do
  sh "env PEX_PYTHON=python3 PEX_VERBOSE=2 #{PEX_FILE}"
end

task :default => :build
