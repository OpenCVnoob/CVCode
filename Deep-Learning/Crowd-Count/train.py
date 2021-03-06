# -*- coding:utf-8 -*-
# ------------------------
# written by Songjian Chen
# 2018-10
# ------------------------
# csr_net: 121.7, 177.4
# mcnn: 121.9, 183.9
from src import utils
from src.datasets import mall_dataset, shtu_dataset
from src.models import csr_net, sa_net, tdf_net, mcnn
import torch
import torch.utils.datas
import torch.optim as optim
import warnings
import sys
import math
import numpy as np
import os
warnings.filterwarnings("ignore")
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
learning_rate = 0.00001
save_path = "./results/mcnn.pkl"
models = {
    'mcnn': utils.weights_normal_init(mcnn.MCNN(bn=True), dev=0.01),
    'csr_net': csr_net.CSRNet(),
    'sa_net': sa_net.SANet(input_channels=1, kernel_size=[1, 3, 5, 7], bias=True),
    'tdf_net': utils.weights_normal_init(tdf_net.TDFNet(), dev=0.01)
}
"""
 load data ->
 init net ->
 backward ->
 test
 zoom size: means reduction rate
 results: mcnn | csr_net | sa_net | tdf_net
 dataset: shtu_dataset | mall_dataset
"""


def train(zoom_size=4, model="mcnn", dataset="shtu_dataset"):
    """

    :type zoom_size: int
    :type model: str
    :type dataset: str

    """
    # load data
    if dataset == "shtu_dataset":
        print("train data loading..........")
        shanghaitech_dataset = shtu_dataset.ShanghaiTechDataset(mode="train", zoom_size=zoom_size)
        tech_loader = torch.utils.data.DataLoader(shanghaitech_dataset, batch_size=1, shuffle=True, num_workers=8)
        print("test data loading............")
        test_data = shtu_dataset.ShanghaiTechDataset(mode="test")
        test_loader = torch.utils.data.DataLoader(test_data, batch_size=1, shuffle=False)
    elif dataset == "mall_dataset":
        print("train data loading..........")
        mall_data = mall_dataset.MallDataset(img_path="./mall_dataset/frames/", point_path="./mall_dataset/mall_gt.mat", zoom_size=zoom_size)
        tech_loader = torch.utils.data.DataLoader(mall_data, batch_size=6, shuffle=True, num_workers=6)
        print("test data loading............")
        mall_test_data = mall_data
        test_loader = torch.utils.data.DataLoader(mall_test_data, batch_size=6, shuffle=False, num_workers=6)
    number = len(tech_loader)
    print("init net...........")
    net = models[model]
    net = net.train().to(DEVICE)
    print("init optimizer..........")
    # optimizer = optim.Adam(filter(lambda p:p.requires_grad, net.parameters()), lr=learning_rate)
    # optimizer = optim.SGD(filter(lambda p:p.requires_grad, net.parameters()), lr=learning_rate, momentum=0.9)
    optimizer = optim.SGD(net.parameters(), lr=1e-7, momentum=0.95, weight_decay=5*1e-4)
    print("start to train net.....")
    sum_loss = 0
    step = 0
    result = []
    epoch_index = -1
    min_mae = sys.maxsize
    # for each 2 epochs in 2000 get and results to test
    # and keep the best one
    for epoch in range(2000):
        for input, ground_truth in iter(tech_loader):
            input = input.float().to(DEVICE)
            ground_truth = ground_truth.float().to(DEVICE)
            output = net(input)
            loss = utils.get_loss(output, ground_truth)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            sum_loss += float(loss)
            step += 1
            if step % (number // 2) == 0:
                print("{0} patches are done, loss: ".format(step), sum_loss / (number // 2))
                sum_loss = 0

        if epoch % 2 == 0:
            sum_mae = 0.0
            sum_mse = 0.0
            for input, ground_truth in iter(test_loader):
                input = input.float().to(DEVICE)
                ground_truth = ground_truth.float().to(DEVICE)
                output = net(input)
                mae, mse = utils.get_test_loss(output, ground_truth)
                sum_mae += float(mae)
                sum_mse += float(mse)
            if sum_mae / len(test_loader) < min_mae:
                min_mae = sum_mae / len(test_loader)
                min_mse = sum_mse / len(test_loader)
                result.append([min_mae, math.sqrt(min_mse)])
                torch.save(net.state_dict(), "./results/mall_result/mcnn.pkl")
            print("best_mae:%.1f, best_mse:%.1f" % (min_mae, math.sqrt(min_mse)))
            epoch_index += 2
            print("{0} epoches / 2000 epoches are done".format(epoch_index))
        step = 0
    result = np.asarray(result)
    try:
        np.save("./results/mall_result/mcnn.npy", result)
    except IOError:
        os.mkdir("./results")
        np.save("./results/mall_result/mcnn.npy", result)
    print("save successful!")


if __name__ == "__main__":
    print("start....")
    model = str(sys.argv[1])
    zoom_size = int(sys.argv[2])
    dataset = str(sys.argv[3])
    print("results: {0}, zoom_size: {1}".format(model, zoom_size))
    train(zoom_size=zoom_size, model=model, dataset=dataset)

