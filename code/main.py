from __future__ import print_function
import torch.backends.cudnn as cudnn
import torch
import torchvision.transforms as transforms

import argparse
import os
import random
import sys
import pprint
import datetime
import dateutil
import dateutil.tz


dir_path = (os.path.abspath(os.path.join(os.path.realpath(__file__), './.')))
sys.path.append(dir_path)

from miscc.datasets import TextDataset, GIFDataset, AudioSet, AudioSet2, AudioSetAudio

from miscc.config import cfg, cfg_from_file
from miscc.utils import mkdir_p
from trainer import GANTrainer, EmbeddingNetTrainer, EmbeddingNetLSTMTrainer



def parse_args():
    parser = argparse.ArgumentParser(description='Train a GAN network')
    parser.add_argument('--cfg', dest='cfg_file',
                        help='optional config file',
                        default='birds_stage1.yml', type=str)
    parser.add_argument('--gpu',  dest='gpu_id', type=str, default='0')
    parser.add_argument('--data_dir', dest='data_dir', type=str, default='')
    parser.add_argument('--manualSeed', type=int, help='manual seed')
    parser.add_argument('--train_emb', action='store_true')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    if args.cfg_file is not None:
        cfg_from_file(args.cfg_file)
    if args.gpu_id != -1:
        cfg.GPU_ID = args.gpu_id
    if args.data_dir != '':
        cfg.DATA_DIR = args.data_dir
    print('Using config:')
    pprint.pprint(cfg)
    if args.manualSeed is None:
        args.manualSeed = random.randint(1, 10000)
    random.seed(args.manualSeed)
    torch.manual_seed(args.manualSeed)
    if cfg.CUDA:
        torch.cuda.manual_seed_all(args.manualSeed)
    now = datetime.datetime.now(dateutil.tz.tzlocal())
    timestamp = now.strftime('%Y_%m_%d_%H_%M_%S')
    debugname = 'debug'
    output_dir = '../output/%s_%s_%s' % \
                 (cfg.DATASET_NAME, cfg.CONFIG_NAME, debugname)

    num_gpu = len(cfg.GPU_ID.split(','))
    if args.train_emb:
        print('Train Embedding Net')
        train_set = AudioSetAudio(cfg.DATA_DIR, True)
        eval_set = AudioSetAudio(cfg.EVAL_DATA_DIR, False)
        trainer = EmbeddingNetTrainer(cfg, output_dir)
        trainer.train(train_set, eval_set)

        output_dir = '../output/%s_%s_%s' % \
                     (cfg.DATASET_NAME, cfg.CONFIG_NAME + 'LSTM', timestamp)
        # trainer = EmbeddingNetLSTMTrainer(cfg, output_dir)
        # trainer.train(train_set, eval_set)
    elif cfg.TRAIN.FLAG:
        image_transform = transforms.Compose([
            transforms.RandomCrop(cfg.IMSIZE),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        eval_dataset = None
        if cfg.DATASET_NAME == 'gif':
            dataset = GIFDataset(cfg.DATA_DIR, cfg.TEXT.DIMENSION, imsize=cfg.IMSIZE, stage=cfg.STAGE)
        elif cfg.DATASET_NAME == 'audioset':
            dataset = AudioSet(cfg.DATA_DIR, frame_hop_size=cfg.VIDEO.HOP_SIZE,
                               n_frames=cfg.VIDEO.N_FRAMES, stage=cfg.STAGE)
            eval_dataset = AudioSet(cfg.EVAL_DATA_DIR, frame_hop_size=cfg.VIDEO.HOP_SIZE,
                               n_frames=cfg.VIDEO.N_FRAMES, stage=cfg.STAGE)
        else:
            dataset = TextDataset(cfg.DATA_DIR, 'train',
                                  imsize=cfg.IMSIZE,
                                  transform=image_transform)
        #print(dataset)
        assert dataset
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=cfg.TRAIN.BATCH_SIZE * num_gpu,
            drop_last=True, shuffle=True, num_workers=int(cfg.WORKERS))

        algo = GANTrainer(output_dir)
        algo.train(dataloader, cfg.STAGE, eval_dataset)
    else:
        datapath= '%s/test/val_captions.t7' % (cfg.DATA_DIR)
        algo = GANTrainer(output_dir)
        algo.sample(datapath, cfg.STAGE)