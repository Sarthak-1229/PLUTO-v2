# PLUTO v2 Phase A Audit Report

Generated: 2026-09-19 13:28:48

## Method

- Sent real HTTP requests through `POST /process` on an isolated, instrumented FastAPI process.
- Timed the actual request path, including classification, KB lookup, web research, LLM calls, report generation, and TTS when reached.
- Counted entries in `knowledge_db.json` before and after every request.
- Preserved complete raw response text below.
- STT is not part of `POST /process`; browser voice input uses the Web Speech API and is therefore reported as not applicable to this endpoint.

## Request Battery

### 1. Smalltalk greeting

- Query: `hi`
- HTTP status: 200
- Total wall clock: 11.610s
- Path taken: smalltalk
- Query classifier: smalltalk
- Intent: chat
- LLM calls: 1
- KB candidates: 0
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.000s; llm_generation=9.626s; local_model_fallback=9.626s; request_handling=9.626s; tts=1.956s
- TTS audio generated: yes

Raw response:

```text
Hello! How can I assist you today? Feel free to ask me any questions or tell me what you'd like to know more about.
```

### 2. Simple math

- Query: `what is 15% of 340`
- HTTP status: 200
- Total wall clock: 4.687s
- Path taken: simple
- Query classifier: simple
- Intent: chat
- LLM calls: 1
- KB candidates: 0
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.001s; llm_generation=3.268s; local_model_fallback=3.268s; request_handling=3.269s; tts=1.390s
- TTS audio generated: yes

Raw response:

```text
To find 15% of 340, you can multiply 340 by 0.15:

\[ 340 \times 0.15 = 51 \]

So, 15% of 340 is 51.
```

### 3. Current-event research

- Query: `who is the current CEO of Nvidia`
- HTTP status: 200
- Total wall clock: 6.806s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 1
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.001s; kb_lookup=0.002s; llm_generation=3.679s; kb_answer_generation=3.679s; request_handling=3.682s; tts=3.092s
- TTS audio generated: yes

Raw response:

```text
The current CEO of NVIDIA as of my last update is Jensen Huang. Jensen Huang has been leading NVIDIA since 1993, when he co-founded the company. He has been instrumental in guiding NVIDIA's growth and development, particularly in the areas of graphics processing units (GPUs) and more recently in artificial intelligence and autonomous vehicles.
```

### 4. Repeated research

- Query: `who is the current CEO of Nvidia`
- HTTP status: 200
- Total wall clock: 8.329s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 1
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.000s; kb_lookup=0.001s; llm_generation=3.607s; kb_answer_generation=3.607s; request_handling=3.609s; tts=4.702s
- TTS audio generated: yes

Raw response:

```text
As of my last update, the current CEO of NVIDIA is Jensen Huang. Jensen Huang has been leading NVIDIA since 1993, when he co-founded the company. He continues to guide the company in its advancements in graphics processing units (GPUs), artificial intelligence, and other technological innovations.
```

### 5. Ambiguous explanatory question

- Query: `explain how binary search works`
- HTTP status: 200
- Total wall clock: 23.498s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 3
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.000s; kb_lookup=0.002s; llm_generation=16.266s; kb_answer_generation=16.266s; request_handling=16.269s; tts=7.200s
- TTS audio generated: yes

Raw response:

```text
Binary search is an efficient algorithm for finding an item from a sorted list of items. It works by repeatedly dividing the search interval in half. Here's a step-by-step explanation of how binary search operates:

1. **Initialization**: Start with the middle element of the list.
2. **Comparison**: If the target value is equal to the middle element, the search is complete.
3. **Search Interval Adjustment**:
   - If the target value is less than the middle element, repeat the search on the left half of the list.
   - If the target value is greater than the middle element, repeat the search on the right half of the list.
4. **Iteration**: Continue this process, each time narrowing the search interval to the half where the target value could be located.
5. **Termination**: The search ends when the target value is found or when the search interval is empty (i.e., the start index is greater than the end index).

Here is a simple Python implementation of binary search:

```python
def binary_search(arr, target):
    start = 0
    end = len(arr) - 1
    
    while start <= end:
        mid = (start + end) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            start = mid + 1
        else:
            end = mid - 1
    
    return -1  # Target not found

# Example usage
arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
target = 7
result = binary_search(arr, target)
print("Index of", target, "is", result)
```

In this example, the function `binary_search` takes a sorted list `arr` and a `target` value, and returns the index of the target value if it exists in the list. If the target is not found, it returns -1.
```

### 6. Vagueness-prone question

- Query: `tell me about machine learning`
- HTTP status: 200
- Total wall clock: 44.901s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 3
- KB entries before/after: 192 / 192 (delta +0)
- Stage timings: classification=0.000s; kb_lookup=0.002s; llm_generation=28.058s; kb_answer_generation=28.058s; request_handling=28.060s; tts=16.778s
- TTS audio generated: yes

Raw response:

```text
Machine learning (ML) is a subfield of artificial intelligence (AI) that focuses on developing algorithms and models that enable computers to learn from and make predictions or decisions based on data, without being explicitly programmed for every task. Here’s a detailed overview:

### Definition and Scope
Machine learning involves creating statistical models that can automatically improve their performance based on data they process. The primary goal is to enable systems to learn and adapt to new data without human intervention, making them more effective and efficient over time.

### Key Components
1. **Data**: The foundation of machine learning. Data can be structured (e.g., databases) or unstructured (e.g., text, images, audio).
2. **Algorithms**: These are the mathematical models that learn from the data. Common types include:
   - **Supervised Learning**: Models are trained on labeled data, where the correct output is known.
   - **Unsupervised Learning**: Models are trained on unlabeled data, where the goal is to find patterns or structure.
   - **Reinforcement Learning**: Models learn through trial and error, receiving rewards or penalties based on their actions.
3. **Performance Evaluation**: Metrics are used to assess how well the model is performing, such as accuracy, precision, recall, F1 score, etc.
4. **Training and Testing**: Data is split into training and testing sets to evaluate the model's performance on unseen data.

### Applications
Machine learning is applied across various domains, including:
- **Healthcare**: Predicting patient outcomes, diagnosing diseases, and personalizing treatment plans.
- **Finance**: Fraud detection, risk assessment, and predictive modeling.
- **Retail**: Personalized recommendations, demand forecasting, and customer segmentation.
- **Autonomous Vehicles**: Object detection, path planning, and decision-making.
- **Natural Language Processing**: Sentiment analysis, language translation, and text summarization.

### Process
1. **Data Collection**: Gathering relevant data from various sources.
2. **Data Preprocessing**: Cleaning and transforming data to make it suitable for modeling.
3. **Model Selection**: Choosing the appropriate algorithm based on the problem and data characteristics.
4. **Training**: The model learns from the training data.
5. **Validation**: Testing the model on a separate validation dataset to fine-tune the model.
6. **Testing**: Evaluating the final model on a test dataset to ensure it performs well on unseen data.
7. **Deployment**: Integrating the model into real-world applications.

### Examples
- **Email Spam Filters**: Using supervised learning to classify emails as spam or not spam.
- **Recommendation Systems**: Recommending products or content based on user behavior.
- **Predictive Maintenance**: Predicting when machines might fail based on sensor data.

### Challenges
- **Overfitting**: Models that perform well on training data but poorly on new data.
- **Underfitting**: Models that are too simple to capture the underlying patterns in the data.
- **Bias and Fairness**: Ensuring that models are unbiased and fair, especially in critical applications like healthcare and finance.
- **Data Privacy**: Handling sensitive data while ensuring compliance with data protection regulations.

### Conclusion
Machine learning is a powerful tool that leverages data to automate decision-making processes and improve the performance of systems. Its applications are vast and continue to grow as technology advances, making it an essential field in the realm of artificial intelligence and data science.

Would you like more detailed information on any specific aspect of machine learning?
```

## UI Audit

- Live/served UI directory: `ui`
- Primary file: `ui\index.html`
- Other UI candidates: `stitch_pluto_ai_agent_interface\code.html`, `ui\test_mathjax.html`
- `Voice Mode` markup/handler found: yes
- `Knowledge Bank` markup/handler found: yes
- `Research Reports` markup/handler found: yes
- `Settings` markup/handler found: yes
- `Chat/send` markup/handler found: yes
- Browser interaction: Not automated in this harness; Phase A includes static control verification and live API checks.
