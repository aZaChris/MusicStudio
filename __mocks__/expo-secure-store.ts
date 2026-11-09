// In-memory stand-in for the Keychain/Keystore in Jest (no native module in Node).
const store = new Map<string, string>();

export const getItemAsync = jest.fn(async (key: string) => store.get(key) ?? null);
export const setItemAsync = jest.fn(async (key: string, value: string) => void store.set(key, value));
export const deleteItemAsync = jest.fn(async (key: string) => void store.delete(key));
export const __reset = () => store.clear();
