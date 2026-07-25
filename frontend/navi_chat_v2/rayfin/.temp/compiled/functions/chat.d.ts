interface FunctionRequest {
    body: {
        question: string;
        language: string;
    };
}
interface FunctionResponse {
    status: number;
    body: {
        answerText: string;
    };
}
export default function chat(request: FunctionRequest): Promise<FunctionResponse>;
export {};
