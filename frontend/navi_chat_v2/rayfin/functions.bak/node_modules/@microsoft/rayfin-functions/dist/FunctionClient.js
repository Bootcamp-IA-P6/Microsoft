/**
 * @packageDocumentation Per-function typed client.
 *
 * Each property on the proxy returned by `createFunctionsApi` is a
 * `FunctionClient` whose `invoke()` signature is derived from the schema
 * entry for that function name.
 */
import { SdkError, NetworkError } from '@microsoft/rayfin-lib';
import { FUNCTIONS_BASE_PATH } from '@microsoft/rayfin-lib';
import { FunctionsError } from './Functions.js';
/**
 * A strongly-typed client for a single function.
 *
 * @typeParam TInput - The parameter object the function expects (`void` when none).
 * @typeParam TOutput - The type returned by the function.
 */
export class FunctionClient {
    apiClient;
    functionName;
    constructor(apiClient, functionName) {
        this.apiClient = apiClient;
        this.functionName = functionName;
    }
    /**
     * Invoke the function and return its typed output.
     *
     * @param args - When the function accepts input, pass
     *   `[params, options?]` — `params` are the input parameters declared
     *   by the function schema, `options` are optional per-call settings
     *   (extra headers, etc.). When the function takes no input, pass
     *   `[options?]` instead.
     * @returns The function's success-path output, typed as `TOutput`.
     *
     * Failure modes throw — a non-empty `errors` array or a non-success
     * status on the wire response is surfaced as {@link FunctionsError}.
     * Network and unknown errors are wrapped in {@link NetworkError} and
     * {@link FunctionsError} respectively. By the time this method
     * resolves, the caller can use the value without defending against
     * `undefined`.
     *
     * The server-side `invocationId` from the underlying envelope is
     * emitted via `console.debug` (along with the function name) so the
     * value is available in the browser/Node console for correlation
     * without polluting the public return type.
     *
     * @throws {@link FunctionsError} - If the function invocation fails.
     * @throws `NetworkError` - For network-related issues.
     * @throws `SdkError` - For any other unexpected SDK errors.
     *
     * @example
     * ```typescript
     * const greeting = await client.functions.helloWorld.invoke({
     *   firstName: 'Ada',
     *   lastName: 'Lovelace',
     * });
     * console.log(greeting); // typed as string
     * ```
     */
    async invoke(...args) {
        try {
            // Unpack the variadic args – when TInput is void the first arg is options.
            let parameters;
            let options;
            if (args.length === 0) {
                // No-arg call: `fn.invoke()`
            }
            else if (args.length === 1) {
                // Could be `invoke(params)` or `invoke(options)` for void-input fns
                const first = args[0];
                if (first &&
                    typeof first === 'object' &&
                    'headers' in first &&
                    Object.keys(first).every((k) => k === 'headers')) {
                    options = first;
                }
                else {
                    parameters = first;
                }
            }
            else {
                parameters = args[0];
                options = args[1];
            }
            // When a `functionsBaseUrl` is configured on the ApiClient (e.g. by
            // local-debug flows that point at a `func start` process), invoke the
            // function directly against `${functionsBaseUrl}/api/<name>` using the
            // Azure Functions Core Tools routing convention. Otherwise fall back to
            // the production path `${baseUrl}/functions/<name>/invoke` handled by
            // the Fabric `InvokeController`.
            const functionsBaseUrl = this.apiClient.getFunctionsBaseUrl();
            const url = functionsBaseUrl
                ? `${functionsBaseUrl}/api/${this.functionName}`
                : `${FUNCTIONS_BASE_PATH}/${this.functionName}/invoke`;
            const response = await this.apiClient.post(url, parameters ?? {}, { headers: options?.headers });
            // Check for errors in the response body
            if (response.errors && response.errors.length > 0) {
                const errorMessage = typeof response.errors[0] === 'string'
                    ? response.errors[0]
                    : JSON.stringify(response.errors[0]);
                throw new FunctionsError(`Function invocation failed: ${errorMessage}`, 'FUNCTION_EXECUTION_ERROR');
            }
            // Check for failed status
            const status = response.status.toLowerCase();
            if (status !== 'success' && status !== 'succeeded') {
                throw new FunctionsError(`Function invocation failed with status: ${response.status}`, 'FUNCTION_EXECUTION_ERROR');
            }
            // Auto-parse JSON-encoded output strings. The Fabric runtime
            // sometimes wraps the user's return value in an inner envelope
            // (a stringified `{ output: <value> }`); peel that off so the
            // caller always sees the original `TOutput`.
            // To-Do Investigate why the double JSON encoding is necessary on the runtime side and whether it can be eliminated.
            let output;
            if (typeof response.output === 'string') {
                try {
                    const parsed = JSON.parse(response.output);
                    if (parsed && typeof parsed === 'object' && 'output' in parsed) {
                        output = parsed.output;
                    }
                    else {
                        output = parsed;
                    }
                }
                catch {
                    // Not JSON — pass through (TOutput may be `string`)
                    output = response.output;
                }
            }
            else {
                output = response.output;
            }
            // Surface invocationId via console.debug so callers can correlate
            // a UI action with server-side telemetry without us having to
            // bake the envelope into the return type. This is opt-in noise
            // that DevTools / Node consoles hide unless the verbose level is
            // turned on.
            if (response.invocationId) {
                console.debug(`[rayfin-functions] ${this.functionName} invocationId=${response.invocationId}`);
            }
            return output;
        }
        catch (error) {
            if (error instanceof FunctionsError ||
                error instanceof NetworkError ||
                error instanceof SdkError) {
                throw error;
            }
            throw new FunctionsError(`An unexpected error occurred during function invocation: ${error.message || error}`, 'UNKNOWN_FUNCTION_ERROR');
        }
    }
}
//# sourceMappingURL=FunctionClient.js.map