import argparse
import os
import random
import numpy as np
import torch
import torch.backends.cudnn as cudnn
import glob

from config import get_config
# from trainer_synapse import trainer_synapse
from trainer_synapse_3 import trainer_synapse
from trainer_ACDC import trainer_ACDC
from network.MSA_MaxNet import net as ViT_seg

parser = argparse.ArgumentParser()
parser.add_argument('--root_path', type=str,
                    default='/data/sjwlab/wuw/data/seg/Synapse', help='root dir for data')
parser.add_argument('--dataset', type=str,
                    default='Synapse', help='experiment_name')
parser.add_argument('--list_dir', type=str,
                    default='./lists/lists_Synapse', help='list dir')
parser.add_argument('--num_classes', type=int,
                    default=9, help='output channel of network')
parser.add_argument('--output_dir', type=str, help='output dir', default="./trained_ckpt")
parser.add_argument('--max_epochs', type=int,
                    default=400, help='maximum epoch number to train')
parser.add_argument('--dice_loss_weight', type=float,
                    default=0.6, help='loss balance factor for the dice loss')
parser.add_argument('--batch_size', type=int,
                    default=8, help='batch_size per gpu')
parser.add_argument('--n_gpu', type=int, default=1, help='total gpu')
parser.add_argument('--deterministic', type=int,  default=1,
                    help='whether use deterministic training')
parser.add_argument('--optimizer', type=str,  default='AdamW',
                    help='the choice of optimizer')
parser.add_argument('--base_lr', type=float,  default=2e-4,
                    help='segmentation network learning rate')
parser.add_argument('--weight_decay', type=float,  default=1e-4,
                    help='weight decay')
parser.add_argument('--clip_grad', type=float,  default=8,
                    help='gradient norm')
parser.add_argument('--lr_scheduler', type=str,  default='cosine',
                    help='the choice of learning rate scheduler')
parser.add_argument('--warmup_epochs', type=int,
                    default=20, help='learning rate warm up epochs')
parser.add_argument('--seed', type=int,
                    default=2222, help='random seed')
parser.add_argument('--cfg', type=str, default="configs/MSA_MaxNet_synapse.yaml",
                    metavar="FILE", help='path to config file', )
parser.add_argument('--resume', help='resume from checkpoint')
args = parser.parse_args()
print(args)

if __name__ == "__main__":
    config = get_config(args.cfg)
    args.img_size = int(config.MODEL.Params.img_size)
    args.backbone = config.MODEL.PRETRAIN_BACKBONE
    args.base_lr = config.MODEL.Params.base_lr
    args.weight_decay = config.MODEL.Params.weight_decay
    args.batch_size = config.MODEL.Params.batch_size

    f = glob.glob(args.output_dir + "/out*")
    if f:
        k = max([int((i.split("/")[-1]).replace("out", "")) for i in f])
    else:
        k = 0
    args.output_dir = args.output_dir + "/out" + str(k + 1)
    os.makedirs(args.output_dir, exist_ok=True)
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    option = vars(args)
    file_name = os.path.join(args.output_dir, 'hyper.txt')
    with open(file_name, 'wt') as opt_file:
        opt_file.write('------------ Options -------------\n')
        for k, v in sorted(option.items()):
            opt_file.write('%s: %s\n' % (str(k), str(v)))
        opt_file.write('-------------- End ----------------\n')

    if args.dataset == "Synapse":
        args.root_path = os.path.join(args.root_path, "train_npz")

    if not args.deterministic:
        cudnn.benchmark = True
        cudnn.deterministic = False
    else:
        cudnn.benchmark = False
        cudnn.deterministic = True

    random.seed(args.seed)
    np.random.seed(args.seed)
    os.environ['PYTHONHASHSEED'] = str(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)

    dataset_name = args.dataset
    dataset_config = {
        'Synapse': {
            'root_path': args.root_path,
            'list_dir': './lists/lists_Synapse',
            'num_classes': args.num_classes,
        },
        'ACDC': {
            'root_path': args.root_path,
            'list_dir': './lists/lists_ACDC',
            'num_classes': args.num_classes,
        },
    }

    if args.batch_size != 24 and args.batch_size % 6 == 0:
        args.base_lr *= args.batch_size / 24
    args.num_classes = dataset_config[dataset_name]['num_classes']
    args.root_path = dataset_config[dataset_name]['root_path']
    args.list_dir = dataset_config[dataset_name]['list_dir']
    torch.cuda.set_device(5)

    net = ViT_seg(model_name=args.backbone,num_classes=args.num_classes,image_size=args.img_size).cuda()
    print(f"param: {sum(p.numel() for p in net.parameters())}")

    trainer = {'Synapse': trainer_synapse, 'ACDC': trainer_ACDC}
    trainer[dataset_name](args, net, args.output_dir)
