from distutils.command.config import config
import torch
import numpy as np
import random
import os
import yaml
import time
import shutil
import glob
import torchvision

__all__ = ['seed_everything', 'parse_device_list', 'allocate_gpus', 'average', 'save_model_per_epoch', 
           'merge_config', 'convert_list_float_type', 'create_folders', 'concate_tensor_lists',
           'weights_init_normal', 'LambdaLR', 'load_model', 'merge_config', 'override_config', 'extract_config',
           'record_path', 'save_arg', 'save_log', 'save_script', 'save_image', 'save_model']

def set_grad(model, flag=True):
    for p in model.parameters():
        p.requires_grad = flag

def convert_list_float_type(l):
    return [float(item) for item in l]

def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # some cudnn methods can be random even after fixing the seed
    # unless you tell it to be deterministic
    torch.backends.cudnn.deterministic = True


def parse_client_data_weights(l):
    for i in range(len(l)):
        l[i] = float(l[i])
        assert isinstance(l[i], float)
    return l


def parse_device_list(device_ids_string, id_choice=None):
    device_ids = [int(i) for i in device_ids_string[0]]
    id_choice = 0 if id_choice is None else id_choice
    device = device_ids[id_choice]
    return device, device_ids


def allocate_gpus(id, num_disc, num_gpus):
    partitions = np.linspace(0, 1, num_gpus, endpoint=False)[1:]
    device_id = 0
    for p in partitions:
        if id <= num_disc * p:
            break
        device_id += 1
    return device_id

def override_config(previous, new):
    config = previous
    for new_key in new.keys():
            config[new_key] = new[new_key]

    return config

def merge_config(config, args):
    """
    args overlaps config, the args is given a high priority 
    """
    for key_arg in dir(args):
        if (getattr(args, key_arg)) and (key_arg in config.keys()):
            config[key_arg] = getattr(args, key_arg)

    return config

def extract_config(args):
    config = dict()
    for key_arg in vars(args):
        if vars(args)[key_arg]:
            config[key_arg] = vars(args)[key_arg]

    return config

def weights_init_normal(m):
    classname = m.__class__.__name__
    if classname.find("Conv") != -1:
        torch.nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif classname.find("BatchNorm2d") != -1:
        torch.nn.init.normal_(m.weight.data, 1.0, 0.02)
        torch.nn.init.constant_(m.bias.data, 0.0)


class LambdaLR:
    def __init__(self, n_epochs, offset, decay_start_epoch):
        assert (
            n_epochs - decay_start_epoch) > 0, "Decay must start before the training session ends!"
        self.n_epochs = n_epochs
        self.offset = offset
        self.decay_start_epoch = decay_start_epoch

    def step(self, epoch):
        return 1.0 - max(0, epoch + self.offset - self.decay_start_epoch) / (self.n_epochs - self.decay_start_epoch)


def record_path(para_dict):
    # mkdir ./work_dir/fed/brats/time-dir
    localtime = time.asctime(time.localtime(time.time()))
    file_path = '{}/centralized/{}/{}'.format(
        para_dict['work_dir'], para_dict['dataset'], localtime)

    if para_dict['federated']:
        file_path = file_path.replace('centralized', 'federated')

    os.makedirs(file_path)

    return file_path


def save_arg(para_dict, file_path):
    with open('{}/config.yaml'.format(file_path), 'w') as f:
        yaml.dump(para_dict, f)


def save_log(infor, file_path, description=None):
    localtime = time.asctime(time.localtime(time.time()))
    infor = '[{}] {}'.format(localtime, infor)

    with open('{}/log{}.txt'.format(file_path, description), 'a') as f:
        print(infor, file=f)


def save_script(src_file, file_path):
    shutil.copy2(src_file, file_path)


def save_image(image, name, image_path):
    if not os.path.exists(image_path):
        os.makedirs(image_path)

    torchvision.utils.save_image(image, '{}/{}'.format(image_path, name), normalize=False)


def save_model(model, file_path, para_dict, psnr, ssim=None, fid=None, kaid=None):
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    for file in glob.glob('{}/*.pth'.format(file_path)):
        os.remove(file)      

    if (ssim is None or fid is None or kaid is None):
        model_path = '{}/best_model_{}_{}_{:.4f}.pth'.format(
            file_path, para_dict['source_domain'], para_dict['target_domain'], psnr)
    else:
        model_path = '{}/best_model_{}_{}_{:.4f}_{:.4f}_{:.4f}.pth'.format(
            file_path, para_dict['source_domain'], para_dict['target_domain'], psnr, ssim, fid, kaid)
    torch.save({'model_state_dict': model.state_dict()}, model_path)

def save_model_per_epoch(model, file_path, para_dict, epoch):
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    for file in glob.glob('{}/*.pth'.format(file_path)):
        os.remove(file)      

    model_path = '{}/{}_{}_{}.pth'.format(
        file_path, para_dict['source_domain'], para_dict['target_domain'], epoch)
    torch.save({'model_state_dict': model.state_dict()}, model_path)

def load_model(model, file_path, description):
    if not os.path.exists(file_path):
        raise ValueError('file is not exist, {}'.format(file_path)) 

    model_path = glob.glob('{}/checkpoint/{}/*.pth'.format(file_path, description))[0]
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['model_state_dict'])

    return model

def create_folders(tag_path):
    if not os.path.exists(tag_path):
        os.makedirs(tag_path)

def average(l):
       return sum(l) / len(l)  

def concate_tensor_lists(imgs_list, img, i):
    if i == 0:
        imgs_list = img
    else: 
        imgs_list = torch.cat((imgs_list, img), 0)
    return imgs_list
    