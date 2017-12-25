require 'tempfile'
require 'tmpdir'

def find_version
  File.read('VERSION').chomp
end

VERSION = find_version
DIST_DIR = 'dist'
BUILD_DIR = './build'
WHEEL_FILE = "#{DIST_DIR}/slyphon_zshhist_backup-#{VERSION}-py3-none-any.whl"
PEX_FILE = "#{DIST_DIR}/schist.pex"


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
    t.close unless t.closed?
  end
end

file PEX_FILE => WHEEL_FILE do
  Dir.mktmpdir do |tmpdir|
    tempfile('other-reqs') do |tmp|
      tmp.puts('schist')
      tmp.flush()
      sh(
        'pex',
        "--pex-root=#{tmpdir}",
        "-r", "requirements.txt",
        "-e", "schist.app:main",
        "--python-shebang=/usr/bin/env python",
        "-o", PEX_FILE,
        "--python=python",
        "-f", DIST_DIR,
        "-r", tmp.path
      )
    end
  end
end

task :build => PEX_FILE

CLEANUP = FileList['dist', 'schist.egg-info', 'build', File.expand_path('~/.pex/install/zshbackup-*')]

task :clean do
  rm_rf CLEANUP
end

task :run do
  Dir.mktmpdir do |tmpdir|
    sh "#{PEX_FILE} help"
  end
end

INSTALL_DIR = File.expand_path("~/local/bin")
INSTALL_DEST = File.join(INSTALL_DIR, "zshhist")

task :install do
  tempfile('zshhist', INSTALL_DIR) do |tmp|
    install PEX_FILE, tmp.path, :mode => 0755
    mv tmp.path, INSTALL_DEST
  end
end


PYVERS = File.read(".python-version").chomp
PYENV_ROOT = File.expand_path('~/.pyenv/versions')

PYTHON_STDLIB_DIR = FileList[File.join(PYENV_ROOT, PYVERS.split('/', 2).first, 'lib', 'python*')]

SITE_PKGS_ROOT = File.join(PYENV_ROOT, PYVERS, 'lib', 'python*', 'site-packages')

REQUIREMENT_NAMES = File.readlines('requirements.txt').map do |n|
  n.chomp[/^([a-zA-Z._-]+)={2}/, 1].tr('-', '_')
end

REQ_SRC = FileList[*REQUIREMENT_NAMES.map { |r| File.join(SITE_PKGS_ROOT, "#{r}*") }]

CTAGSIFY = FileList['schist/**/*.py'] + PYTHON_STDLIB_DIR + REQ_SRC

task :ctags do
  sh "ctags", "-R", *CTAGSIFY
end

task :test do
  sh "tox"
end

task :all => [:clean, :build, :run]

task :default => :all
