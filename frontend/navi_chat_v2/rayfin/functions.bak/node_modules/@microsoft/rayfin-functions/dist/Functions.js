/**
 * @packageDocumentation Functions API for invoking serverless functions.
 *
 * The single public surface is `client.functions.<name>.invoke(...)` where
 * `<name>` is constrained by the `FunctionsSchema` type parameter passed to
 * `RayfinClient`.
 *
 * ```ts
 * const res = await client.functions.helloWorld.invoke({ firstName: 'Ada' });
 * ```
 */
import { SdkError } from '@microsoft/rayfin-lib';
import { FunctionClient } from './FunctionClient.js';
export { FunctionClient } from './FunctionClient.js';
/**
 * Functions error specific to the Rayfin SDK.
 */
export class FunctionsError extends SdkError {
    constructor(message, code) {
        super(message, code || 'FUNCTIONS_ERROR');
    }
}
/**
 * Create a typed `client.functions` proxy that lazily instantiates and caches
 * a {@link FunctionClient} per schema-defined function name.
 *
 * ```ts
 * const fns = createFunctionsApi<MyFunctionsSchema>(apiClient);
 * const res = await fns.helloWorld.invoke({ firstName: 'Ada' });
 * ```
 */
export function createFunctionsApi(apiClient) {
    const cache = new Map();
    const get = (name) => {
        let client = cache.get(name);
        if (!client) {
            client = new FunctionClient(apiClient, name);
            cache.set(name, client);
        }
        return client;
    };
    return new Proxy(Object.create(null), {
        get(_target, prop) {
            if (typeof prop !== 'string')
                return undefined;
            return get(prop);
        },
        has(_target, prop) {
            return typeof prop === 'string';
        },
        ownKeys() {
            return Array.from(cache.keys());
        },
        getOwnPropertyDescriptor(_target, prop) {
            if (typeof prop !== 'string')
                return undefined;
            return {
                enumerable: true,
                configurable: true,
                value: get(prop),
            };
        },
    });
}
//# sourceMappingURL=Functions.js.map