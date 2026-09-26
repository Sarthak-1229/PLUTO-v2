# PLUTO v2 Phase A Audit Report

Generated: 2026-09-20 16:16:14

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
- Total wall clock: 18.926s
- Path taken: smalltalk
- Query classifier: smalltalk
- Intent: chat
- LLM calls: 1
- KB candidates: 0
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.000s; llm_generation=16.464s; request_handling=16.465s; tts=2.451s
- TTS audio generated: yes

Raw response:

```text
Hello there! How can I assist you today?
```

### 2. Simple math

- Query: `what is 15% of 340`
- HTTP status: 200
- Total wall clock: 2.620s
- Path taken: simple
- Query classifier: simple
- Intent: chat
- LLM calls: 1
- KB candidates: 0
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.001s; llm_generation=1.460s; request_handling=1.461s; tts=1.150s
- TTS audio generated: yes

Raw response:

```text
15% of 340 is 51.
```

### 3. Current-event research

- Query: `who is the current CEO of Nvidia`
- HTTP status: 200
- Total wall clock: 13.848s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 1
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.001s; kb_lookup=0.003s; llm_generation=12.175s; kb_answer_generation=12.175s; request_handling=12.179s; tts=1.635s
- TTS audio generated: yes

Raw response:

```text
The current CEO of Nvidia is Jensen Huang. Jensen Huang has held this position since 1993 when Nvidia was founded. There have been no changes in the CEO position since its inception.
```

### 4. Repeated research

- Query: `who is the current CEO of Nvidia`
- HTTP status: 200
- Total wall clock: 5.455s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 1
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.000s; kb_lookup=0.002s; llm_generation=2.891s; kb_answer_generation=2.891s; request_handling=2.893s; tts=2.552s
- TTS audio generated: yes

Raw response:

```text
The current CEO of Nvidia is Jensen Huang. Jensen Huang has been leading Nvidia since 1993, when the company was founded. As of the latest information, there have been no changes in his leadership position.
```

### 5. Ambiguous explanatory question

- Query: `explain how binary search works`
- HTTP status: 200
- Total wall clock: 36.256s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 3
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.000s; kb_lookup=0.003s; llm_generation=28.205s; kb_answer_generation=28.205s; request_handling=28.208s; tts=7.995s
- TTS audio generated: yes

Raw response:

```text
Binary search is an efficient algorithm for finding an item from a sorted list of items. It works by repeatedly dividing the search interval in half. Here’s a step-by-step explanation:

1. **Initialize the search interval**: Start with the entire list. Let's say the list is sorted in ascending order, and we are searching for a specific value, `target`.

2. **Find the middle element**: Calculate the middle index of the current search interval. For a list of size `n`, the middle index is `n/2` (integer division).

3. **Compare the middle element with the target**:
   - If the middle element is equal to the target, the search is complete.
   - If the middle element is less than the target, discard the left half of the list and repeat the search on the right half.
   - If the middle element is greater than the target, discard the right half of the list and repeat the search on the left half.

4. **Repeat the process**: Continue dividing the search interval in half and comparing the middle element with the target until the target is found or the search interval is empty.

5. **Return the result**: If the target is found, return its index. If the target is not found, return a value indicating that the target is not in the list (e.g., `-1`).

Here’s a concrete example:

Suppose we have a sorted list: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` and we are searching for the number `7`.

1. **Initialize the search interval**: The list is `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`.
2. **Find the middle element**: The middle index is `5` (since `10/2 = 5`), and the middle element is `6`.
3. **Compare the middle element with the target**: `6` is less than `7`, so we discard the left half and search in the right half `[7, 8, 9, 10]`.
4. **Repeat the process**:
   - New middle index is `7` (since `4/2 = 2`), and the middle element is `9`.
   - `9` is greater than `7`, so we discard the right half and search in the left half `[7, 8]`.
   - New middle index is `8` (since `2/2 = 1`), and the middle element is `8`.
   - `8` is greater than `7`, so we discard the right half and search in the left half `[7]`.
   - New middle index is `9` (since `1/2 = 0`), and the middle element is `7`.
   - `7` is equal to `7`, so the search is complete.

The target `7` is found at index `6` (0-based index).

Binary search has a time complexity of O(log n), making it very efficient for large datasets.
```

### 6. Vagueness-prone question

- Query: `tell me about machine learning`
- HTTP status: 200
- Total wall clock: 56.101s
- Path taken: knowledge_base_cache
- Query classifier: research
- Intent: chat
- LLM calls: 1
- KB candidates: 3
- KB entries before/after: 196 / 196 (delta +0)
- Stage timings: classification=0.001s; kb_lookup=0.003s; llm_generation=39.213s; kb_answer_generation=39.213s; request_handling=39.217s; tts=16.806s
- TTS audio generated: yes

Raw response:

```text
Machine learning (ML) is a field within artificial intelligence (AI) that focuses on developing algorithms and statistical models that enable computers to learn from and make predictions or decisions based on data, without being explicitly programmed for every specific task. Here’s a more detailed overview:

### Key Components and Concepts

1. **Statistical Algorithms**:
   - Machine learning relies on statistical algorithms that can process and analyze large datasets to identify patterns and relationships.

2. **Learning from Data**:
   - The primary goal of ML is to develop models that can learn from training data and use that learning to make accurate predictions or decisions on new, unseen data.

3. **Types of Machine Learning**:
   - **Supervised Learning**: Involves training a model on labeled data, where each data point is associated with a known output. The model learns to map inputs to outputs. Common applications include image classification and speech recognition.
   - **Unsupervised Learning**: Deals with unlabeled data, where the goal is to find hidden patterns or intrinsic structures in the data. Examples include clustering and dimensionality reduction.
   - **Reinforcement Learning**: Involves an agent learning to make decisions in an environment by performing actions and receiving rewards or penalties. This type of learning is common in game playing and robotics.

### Process of Machine Learning

1. **Data Collection**:
   - Gather relevant data from various sources. This can include structured data from databases or unstructured data from the web, social media, etc.

2. **Data Preprocessing**:
   - Clean and preprocess the data to remove noise and inconsistencies, and transform it into a format suitable for model training. This includes tasks like normalization, feature scaling, and handling missing values.

3. **Feature Selection**:
   - Identify the most relevant features that contribute to the predictive power of the model. This can be done manually or using automated feature selection techniques.

4. **Model Selection**:
   - Choose an appropriate algorithm based on the problem type and the nature of the data. Popular algorithms include decision trees, support vector machines, neural networks, and ensemble methods like random forests and gradient boosting.

5. **Training the Model**:
   - Use the training data to train the selected model. During training, the model learns the patterns and relationships in the data.

6. **Evaluation**:
   - Evaluate the model's performance using a validation dataset. Common metrics include accuracy, precision, recall, and F1 score.

7. **Tuning and Optimization**:
   - Fine-tune the model parameters to improve its performance. This can involve adjusting hyperparameters and using techniques like cross-validation.

8. **Deployment**:
   - Once the model is optimized, deploy it in a production environment where it can make real-time predictions or decisions.

### Real-World Applications

- **Healthcare**: Predicting patient outcomes, disease diagnosis, and personalized treatment plans.
- **Finance**: Fraud detection, risk assessment, and algorithmic trading.
- **Retail**: Customer segmentation, recommendation systems, and inventory management.
- **Autonomous Vehicles**: Object detection, path planning, and decision-making.
- **Natural Language Processing**: Sentiment analysis, language translation, and chatbots.

### Example: Predicting House Prices

Suppose you want to predict house prices based on features like size, location, and age. You would:

1. **Collect Data**: Gather a dataset of houses with their prices and features.
2. **Preprocess Data**: Clean the data, handle missing values, and normalize the features.
3. **Select Model**: Choose a regression model like linear regression or a more complex model like a neural network.
4. **Train Model**: Use the training data to train the model.
5. **Evaluate Model**: Use a validation set to evaluate the model's performance.
6. **Tune Model**: Adjust parameters to improve accuracy.
7. **Deploy Model**: Use the model to predict house prices in real-time.

Machine learning is a powerful tool that has transformed many industries by enabling systems to learn and adapt to new data, making it an essential part of modern AI applications.
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
