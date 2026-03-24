const childProcess = require('node:child_process')
const { syncBuiltinESMExports } = require('node:module')

const originalExec = childProcess.exec

childProcess.exec = function patchedExec(command, ...args) {
  if (process.platform === 'win32' && command === 'net use') {
    const callback = typeof args.at(-1) === 'function' ? args.at(-1) : null
    if (callback) {
      process.nextTick(() => callback(new Error('Skipped net use lookup for Vitest on Windows.'), '', ''))
    }
    return {
      kill() {},
      on() {
        return this
      },
      once() {
        return this
      },
      stdout: null,
      stderr: null,
    }
  }

  return originalExec.call(this, command, ...args)
}

syncBuiltinESMExports()
