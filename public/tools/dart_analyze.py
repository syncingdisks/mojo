#!/usr/bin/python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# To integrate dartanalyze with our build system, we take an input file, run
# the analyzer on it, and write a stamp file if it passed.

# This script analyzes a set of entrypoints specified with the --entrypoints
# flag. The location of the Dart SDK must be specified with the --dart-sdk
# flag. A stamp file can optionally be written with the location given by the
# --stamp-file flag. Any command line arguments not recognized by this script
# are passed on to the Dart analyzer.

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

_IGNORED_PATTERNS = [
  # Ignored because they're not indicative of specific errors.
  re.compile(r'^$'),
  re.compile(r'^Analyzing \['),
  re.compile(r'^No issues found'),
  re.compile(r'^[0-9]+ errors? and [0-9]+ warnings? found.'),
  re.compile(r'^([0-9]+|No) (error|warning|issue)s? found.'),

  # TODO: It seems like this should be re-enabled evenutally.
  re.compile(r'.*is a part and can not|^Only libraries can be analyzed'),
  # TODO: Remove this once dev SDK includes Uri.directory constructor.
  re.compile(r'.*The class \'Uri\' does not have a constructor \'directory\''),
  # TODO: Remove this once Sky no longer generates this warning.
  # dartbug.com/22836
  re.compile(r'.*cannot both be unnamed'),

  # The Dart SDK seems to generate some hints and lints.
  re.compile(r'.*\/dart-sdk\/'),
]


def _success(stamp_file):
  # We passed cleanly, so touch the stamp file so that we don't run again.
  with open(stamp_file, 'a'):
    os.utime(stamp_file, None)
  return 0


def analyze_and_filter(cmd, temp_dir=None, dirname=None):
  errors = None
  try:
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    errors = set(l for l in e.output.split('\n')
                 if not any(p.match(l) for p in _IGNORED_PATTERNS))
    for error in sorted(errors):
      if dirname is None:
        print >> sys.stderr, error
      else:
        print >> sys.stderr, error.replace(temp_dir + "/", dirname)
  return errors


def analyze_entrypoints(dart_sdk, entrypoints, args):
  cmd = [ os.path.join(dart_sdk, 'bin', 'dartanalyzer') ]
  cmd.extend(entrypoints)
  cmd.extend(args)
  cmd.append("--fatal-warnings")
  cmd.append("--fatal-lints")
  cmd.append("--fatal-hints")
  errors = analyze_and_filter(cmd)
  if errors is None:
    return 0
  return min(255, len(errors))


def main():
  parser = argparse.ArgumentParser(description='Run the Dart analyzer.')
  parser.add_argument('--dart-sdk',
                      action='store',
                      type=str,
                      metavar='dart_sdk',
                      help='Path to the Dart SDK',
                      required=True)
  parser.add_argument('--stamp-file',
                      action='store',
                      type=str,
                      metavar='stamp_file',
                      help='Stamp file to write on success.',
                      default=None)
  parser.add_argument('--entrypoints',
                      help='Entry points to analyze',
                      nargs='*',
                      default=[])
  args, remainder = parser.parse_known_args()

  if args.entrypoints == []:
    parser.print_help()
    return 1

  return analyze_entrypoints(args.dart_sdk, args.entrypoints, remainder)

if __name__ == '__main__':
  sys.exit(main())
