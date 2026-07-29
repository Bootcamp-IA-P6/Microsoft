export type AppFunctionsSchema = {
    chat: {
        input: {
            question: string;
            language: string;
        };
        output: {
            answerText: string;
        };
    };
};
