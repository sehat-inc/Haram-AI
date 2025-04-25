import pickle
import numpy as np
from tensorflow.keras.preprocessing.sequence import pad_sequences
import onnxruntime as ort

from preprocess import preprocess_ingredients

with open('tokenizer.pickle', 'rb') as f:
    tokenizer = pickle.load(f)

sess = ort.InferenceSession("lstm_haram.onnx")
input_meta  = sess.get_inputs()[0]
input_name  = input_meta.name
output_name = sess.get_outputs()[0].name

class_labels = {0: "Halal", 1: "Haram"}

def predict_texts_single(texts,
                         tokenizer,
                         session,
                         input_name,
                         output_name,
                         maxlen=None):
    
    # Determine padding length
    if maxlen is None:
        # input_meta.shape is like [1, maxlen]
        maxlen = input_meta.shape[1]

    preds = []
    for txt in texts:
        # 1) Tokenize & pad single text
        seq = tokenizer.texts_to_sequences([txt])
        x = pad_sequences(seq, maxlen=maxlen).astype(np.int32)  # shape (1, maxlen)

        # 2) Run inference
        out = session.run([output_name], {input_name: x})[0]     # (1, num_classes)
        pred = np.argmax(out, axis=1)[0]                        # single int
        preds.append(pred)

    return np.array(preds)

def infer(ingredients):

    cleaned_ingredients = preprocess_ingredients(ingredients)
    texts = [cleaned_ingredients]
    pred = predict_texts_single(
        texts=texts,
        tokenizer=tokenizer,
        session=sess,
        input_name=input_name,
        output_name=output_name
    )

    for text, prediction in zip(texts, pred):
        return class_labels[prediction]