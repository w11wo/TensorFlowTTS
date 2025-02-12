# -*- coding: utf-8 -*-
# Copyright 2020 TensorFlowTTS Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Perform preprocessing and raw feature extraction for English IPA dataset."""

import os
import re
from string import punctuation

import numpy as np
import soundfile as sf
from dataclasses import dataclass

from gruut import sentences

from tensorflow_tts.processor.base_processor import BaseProcessor
from tensorflow_tts.utils.utils import PROCESSOR_FILE_NAME

valid_symbols = [
    "aɪ",
    "aʊ",
    "b",
    "d",
    "d͡ʒ",
    "eɪ",
    "f",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "oʊ",
    "p",
    "s",
    "t",
    "t͡ʃ",
    "u",
    "v",
    "w",
    "z",
    "æ",
    "ð",
    "ŋ",
    "ɑ",
    "ɔ",
    "ə",
    "ɚ",
    "ɛ",
    "ɡ",
    "ɪ",
    "ɹ",
    "ʃ",
    "ʊ",
    "ʌ",
    "ʒ",
    "ˈaɪ",
    "ˈaʊ",
    "ˈeɪ",
    "ˈi",
    "ˈoʊ",
    "ˈu",
    "ˈæ",
    "ˈɑ",
    "ˈɔ",
    "ˈɔɪ",
    "ˈɚ",
    "ˈɛ",
    "ˈɪ",
    "ˈʊ",
    "ˈʌ",
    "ˌaɪ",
    "ˌaʊ",
    "ˌeɪ",
    "ˌi",
    "ˌoʊ",
    "ˌu",
    "ˌæ",
    "ˌɑ",
    "ˌɔ",
    "ˌɔɪ",
    "ˌɚ",
    "ˌɛ",
    "ˌɪ",
    "ˌʊ",
    "ˌʌ",
    "θ",
]

_punctuation = "!,.?;:"
_sil = "@SIL"
_eos = "@EOS"
_pad = "@PAD"
_ipa = ["@" + s for s in valid_symbols]

ENGLISH_IPA_SYMBOLS = [_pad] + _ipa + list(_punctuation) + [_sil] + [_eos]


@dataclass
class EnglishIPAProcessor(BaseProcessor):

    mode: str = "train"
    train_f_name: str = "train.txt"
    positions = {
        "file": 0,
        "text": 1,
        "speaker_name": 2,
    }  # positions of file,text,speaker_name after split line
    f_extension: str = ".wav"
    cleaner_names: str = None

    def create_items(self):
        with open(
            os.path.join(self.data_dir, self.train_f_name), mode="r", encoding="utf-8"
        ) as f:
            for line in f:
                parts = line.strip().split(self.delimiter)
                wav_path = os.path.join(self.data_dir, parts[self.positions["file"]])
                wav_path = (
                    wav_path + self.f_extension
                    if wav_path[-len(self.f_extension) :] != self.f_extension
                    else wav_path
                )
                text = parts[self.positions["text"]]
                speaker_name = parts[self.positions["speaker_name"]]
                self.items.append([text, wav_path, speaker_name])

    def get_one_sample(self, item):
        text, wav_path, speaker_name = item
        audio, rate = sf.read(wav_path, dtype="float32")

        text_ids = np.asarray(self.text_to_sequence(text), np.int32)

        sample = {
            "raw_text": text,
            "text_ids": text_ids,
            "audio": audio,
            "utt_id": wav_path.split("/")[-1].split(".")[0],
            "speaker_name": speaker_name,
            "rate": rate,
        }

        return sample

    def setup_eos_token(self):
        return None

    def save_pretrained(self, saved_path):
        os.makedirs(saved_path, exist_ok=True)
        self._save_mapper(os.path.join(saved_path, PROCESSOR_FILE_NAME), {})

    def text_to_sequence(self, text):
        if (
            self.mode == "train"
        ):  # in train mode text should be already transformed to phonemes
            return self.symbols_to_ids(self.clean_g2p(text.split()))
        else:
            return self.inference_text_to_seq(text)

    def inference_text_to_seq(self, text: str):
        return self.symbols_to_ids(self.text_to_ph(text))

    def symbols_to_ids(self, symbols_list: list):
        return [self.symbol_to_id[s] for s in symbols_list]

    def text_to_ph(self, text: str):
        phn_arr = []
        for words in sentences(text):
            for word in words:
                if word.is_major_break or word.is_minor_break:
                    phn_arr += [word.text]
                elif word.phonemes:
                    phn_arr += word.phonemes

        return self.clean_g2p(phn_arr)

    def clean_g2p(self, g2p_text: list):
        data = []
        for txt in g2p_text:
            if txt in punctuation:
                data.append(txt)
            elif txt != " ":
                data.append("@" + txt)
        return data
