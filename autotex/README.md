#autotex
*Autotex* is tool to automatize the *LaTeX* compilation process. It is very similar to *latexmk* but provides a cleaner interface, some extra features and is written in [*Python 3*](https://www.python.org/).

 - [Requirements](#requirements)
 - [Usage](#usage)
   - [Input Files](#input-files)
   - [Continues Mode](#continues-mode)
 - [Configuration](#configuration)
   - [`append_log`](#append_log)
   - [`basedir`](#basedir)
   - [`command_map`](#command_map)
   - [`continuously`](#continuously)
   - [`continuously_wait`](#continuously_wait)
   - [`log`](#log)
   - [`max_rounds`](#max_rounds)
   - [`print_stdout`](#print_stdout)
   - [`print_stderr`](#print_stderr)
   - [`state`](#state)
   - [`tmpdir`](#tmpdir)
   - [`verbose`](#vebose)

##Requirements
Apart from *Python 3* itself, [*PyYAML*](http://pyyaml.org/) is required. You can install it using you distribution package manager or pip.

##Usage
To compile a .tex file just run

    autotex whatever.tex

*Autotex* will call all required programs and will track all local file dependencies. The state gets saved to `.autotex.state` so you can rerun *autotex* whenever you changed a file.

###Input Files
You can pass multiple input files at once if required. This is helpful when building a class or package file and the documentation at the same time. Please note that changing input files requires you to delete the state file.

###Continues Mode
Using the `-e` flag starts *autotex* in continues mode, so it will wait when all tasks are finished and automatically rerun when files are changed.

##Configuration
*Autotex* reads the `.autotexrc` file at startup and patches its internal configuration. The config file is written in [*YAML*](http://en.wikipedia.org/wiki/YAML) but has some extra patching syntax. For example, if a dictionary key starts with `?+` it is merged with the actual configuration instead of overwritten. Dictionary keys and list entries starting with `?-` are removed from the original config. The patch order is `command line` > `config file` > `buildin`.

The following sections describe all config options.

###`append_log`
Describes if the log file is overwritten or if new data gets appended.

**Values:** `true` => new data gets appended, `false` => log file gets overwritten

**Default:** `false`

###`basedir`
The base directory for all relative paths and the local file filtering.

**Values:** String that describes relative or absolute paths

**Default:** the current working directory

###`command_map`
Maps filenames to actions. The keys are regular expressions to match filenames and the value is a dictionary containing the following parts:

 - `type`: Python class of the action
 - `args`: constructor arguments
 - `auto`: `true` => actions get created as dependency, `false` actions get only created at program start, defaults to `false`

###`continuously`
Activates continues mode.

**Values:** `true` => continues mode, `false` => exit when nothing to do

**Default:** `false`

###`continuously_wait`
Wait time for continues mode in seconds.

**Values:** seconds as float value

**Default:** 3

###`log`
Log file path

**Values:** String, absolute or relative log file path and name

**Default:** `autotex.log`

###`max_rounds`
Maximum tries to reach a fix point. If there are actions that require execution after this number of rounds *autotex* returns an error. A round contains checking and execution of all registered actions. In continues mode the counter gets reseted when nothing is to do.

**Values:** integer value, `0` means that a unlimited number of rounds is legal

**Default:** 10

###`print_stdout`
Controls if the standard output of the executed programs gets printed to the console.

**Values:** `true` => output gets printed, `false` => you have to check the log file for the output

**Default:** `false`

###`print_stderr`
Controls if the standard error channel of the executed programs gets printed to the console.

**Values:** `true` => error channel gets printed, `false` => you have to check the log file for errors

**Default:** `true`

###`state`
Filename of the state file

**Values:** String, absolute or relative path

**Default:** `.autotex.state`

###`tmpdir`
Directory to store some temporary data during the execution

**Values:** string, absolute or relative path

**Default:** OS dependent temporary dictionary, gets removed after execution

###`verbose`
Controls if debug information gets printed to the console

**Values:** `true` => you like debug output, `false` => you don't care

**Default:** `false`

