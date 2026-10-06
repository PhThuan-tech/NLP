"""One explicit mBART language contract for training and every inference path."""

LANGUAGE_CONTROL_VERSION = 1
LANGUAGES = {"en2vi": ("en_XX", "vi_VN"), "vi2en": ("vi_VN", "en_XX")}


def configure_tokenizer(tokenizer, direction):
    source, target = LANGUAGES[direction]
    tokenizer.src_lang = source
    tokenizer.tgt_lang = target
    ids = {}
    for language in (source, target):
        token_id = tokenizer.convert_tokens_to_ids(language)
        if token_id is None or token_id == tokenizer.unk_token_id:
            raise ValueError(f"Tokenizer lacks language token {language}")
        ids[language] = token_id
    # Exercise the real target mode: attributes alone do not prove correct encoding.
    source_ids = tokenizer("Language check", add_special_tokens=True)["input_ids"]
    target_ids = tokenizer(text_target="Kiểm tra ngôn ngữ", add_special_tokens=True)["input_ids"]
    if source_ids[-1] != ids[source] or target_ids[-1] != ids[target]:
        raise ValueError("Tokenizer did not append the expected source/target language tokens")
    return tokenizer


def configure_model(model, tokenizer, direction):
    target = LANGUAGES[direction][1]
    token_id = tokenizer.convert_tokens_to_ids(target)
    if token_id is None or token_id == tokenizer.unk_token_id:
        raise ValueError(f"Invalid target language token: {target}")
    if token_id >= model.config.vocab_size:
        raise ValueError("Language token is outside the model vocabulary")
    for config in (model.config, model.generation_config):
        config.decoder_start_token_id = token_id
        # mBART-25 starts with the target language; do not force a second BOS.
        config.forced_bos_token_id = None
    return model
