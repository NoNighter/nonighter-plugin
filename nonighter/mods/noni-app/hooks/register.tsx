// Placeholder. sync-skills installs a NoNighter mod into this folder for a licence that includes it.
// Until then this empty module stands in: the plugin's hooks.json names this path, and without a module
// here Claude would report the whole plugin as "failed to load". The .placeholder file at this folder's
// root is what tells sync-skills the folder is a stand-in it may replace.
import type { Register } from 'claude-code'

export const register: Register = () => {}
