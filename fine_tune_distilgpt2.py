from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments
from datasets import Dataset
import json
import torch

def fine_tune_model():
    with open('roast_templates.json', 'r') as f:
        templates = json.load(f)
    training_data = []
    for category, levels in templates.items():
        for level, roasts in levels.items():
            for roast in roasts:
                training_data.append(roast.format(name="example", depth="3", score="10", issue="example issue"))
    dataset_dict = {"text": training_data}
    dataset = Dataset.from_dict(dataset_dict)
    tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained('distilgpt2')
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    tokenized_dataset.set_format("torch", columns=["input_ids", "attention_mask"])
    data_collator = lambda data: {
        'input_ids': torch.stack([f['input_ids'] for f in data]),
        'attention_mask': torch.stack([f['attention_mask'] for f in data]),
        'labels': torch.stack([f['input_ids'] for f in data])
    }
    training_args = TrainingArguments(
        output_dir='./fine_tuned_distilgpt2',
        overwrite_output_dir=True,
        num_train_epochs=2,
        per_device_train_batch_size=1,
        save_steps=500,
        save_total_limit=2,
        logging_steps=100,
        use_cpu=True,
        fp16=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )
    try:
        trainer.train()
        trainer.save_model('./fine_tuned_distilgpt2')
        tokenizer.save_pretrained('./fine_tuned_distilgpt2')
    except Exception as e:
        print(f"Fine-tuning failed: {e}. Using pre-trained model.")

if __name__ == "__main__":
    fine_tune_model()