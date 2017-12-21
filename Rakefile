require 'tempfile'
require 'tmpdir'

def find_version
  line = File.open('setup.py') { |fp| fp.readlines.find { |n| n =~ /@@VERSION@@/ } }
  raise "could not read version from setup.py" if line.nil?
  v = line[/VERSION=['"]([^'"]+)['"]/, 1]
  raise "failed to extract version from line: #{line}" if v.nil?
  v
end

VERSION = find_version
DIST_DIR = 'dist'
BUILD_DIR = './build'
WHEEL_FILE = "#{DIST_DIR}/slyphon_zshhist_backup-#{VERSION}-py3-none-any.whl"
PEX_FILE = "#{DIST_DIR}/zshhist.pex"


directory DIST_DIR
directory BUILD_DIR

file WHEEL_FILE => [DIST_DIR, BUILD_DIR] do
  sh "pip3 --no-cache-dir wheel -b #{BUILD_DIR} -w #{DIST_DIR} ."
end

task :wheel => WHEEL_FILE

def tempfile(*a)
  t = Tempfile.new(*a)
  begin
    yield t
  ensure
    t.close
  end
end

file PEX_FILE => WHEEL_FILE do
  Dir.mktmpdir do |tmpdir|
    tempfile('other-reqs') do |tmp|
      tmp.puts('zshbackup')
      tmp.flush()
      cmd = "pex --pex-root=#{tmpdir} -r requirements.txt -e zshbackup.app:main --python-shebang='/usr/bin/env python3' "
      cmd += "-o #{PEX_FILE} --python=python3 -f #{DIST_DIR} -r #{tmp.path}"
      sh(cmd)
    end
  end
end

CLEANUP = FileList['dist', 'zshbackup.egg-info', 'build', File.expand_path('~/.pex/install/zshbackup-*')]

task :build => PEX_FILE

task :clean do
  rm_rf CLEANUP
end

task :run do
  Dir.mktmpdir do |tmpdir|
    sh "env PEX_ROOT=#{tmpdir} PEX_VERBOSE=2 #{PEX_FILE}"
  end
end

task :all => [:clean, :build, :run]

task :default => :all
