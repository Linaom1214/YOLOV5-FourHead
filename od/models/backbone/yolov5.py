import torch.nn as nn
from od.models.modules.common import Focus, Conv, C3, SPP, BottleneckCSP
from utils.general import make_divisible


class YOLOv5(nn.Module):
    def __init__(self, focus=True, version='L'):
        super(YOLOv5, self).__init__()
        self.version = version
        self.with_focus = focus

        gains = {'s': {'gd': 0.33, 'gw': 0.5},
                 'm': {'gd': 0.67, 'gw': 0.75},
                 'l': {'gd': 1, 'gw': 1},
                 'x': {'gd': 1.33, 'gw': 1.25}}
        self.gd = gains[self.version.lower()]['gd']  # depth gain
        self.gw = gains[self.version.lower()]['gw']  # width gain

        self.channels_out = {
            'stage1': 64,
            'stage2_1': 128,
            'stage2_2': 128,
            'stage3_1': 256,
            'stage3_2': 256,
            'stage4_1': 512,
            'stage4_2': 512,
            'stage5': 1024,
            'spp': 1024,
            'csp1': 1024,
            'conv1': 512
        }
        self.re_channels_out()

        if self.with_focus:
            self.stage1 = Focus(3, self.channels_out['stage1'])
        else:
            self.stage1 = Conv(3, self.channels_out['stage1'], 3, 2)

        # for latest yolov5, you can change BottleneckCSP to C3
        self.stage2_1 = Conv(self.channels_out['stage1'], self.channels_out['stage2_1'], k=3, s=2)
        self.stage2_2 = BottleneckCSP(self.channels_out['stage2_1'], self.channels_out['stage2_2'], self.get_depth(3))
        self.stage3_1 = Conv(self.channels_out['stage2_2'], self.channels_out['stage3_1'], 3, 2)
        self.stage3_2 = BottleneckCSP(self.channels_out['stage3_1'], self.channels_out['stage3_2'], self.get_depth(9))
        self.stage4_1 = Conv(self.channels_out['stage3_2'], self.channels_out['stage4_1'], 3, 2)
        self.stage4_2 = BottleneckCSP(self.channels_out['stage4_1'], self.channels_out['stage4_2'], self.get_depth(9))
        self.stage5 = Conv(self.channels_out['stage4_2'], self.channels_out['stage5'], 3, 2)
        self.spp = SPP(self.channels_out['stage5'], self.channels_out['spp'], [5, 9, 13])
        self.csp1 = BottleneckCSP(self.channels_out['spp'], self.channels_out['csp1'], self.get_depth(3), False)
        self.conv1 = Conv(self.channels_out['csp1'], self.channels_out['conv1'], 1, 1)
        self.out_shape = {
            'C2_size': self.channels_out['stage2_2'],
            'C3_size': self.channels_out['stage3_2'],
            'C4_size': self.channels_out['stage4_2'],
            'C5_size': self.channels_out['conv1']}
        print("backbone output channel: C2 {} C3 {}, C4 {}, C5 {}".format(
            self.channels_out['stage2_2'],
            self.channels_out['stage3_2'],
            self.channels_out['stage4_2'],
            self.channels_out['conv1']))

    def forward(self, x):
        x = self.stage1(x)  # 416 --> 208
        x21 = self.stage2_1(x) # 208 -> 104 
        x22 = self.stage2_2(x21) # 104 -> 104
        x31 = self.stage3_1(x22) # 104 -> 52
        c3 = self.stage3_2(x31)  # 52 -> 52
        x41 = self.stage4_1(c3)  # 52 -> 26 
        c4 = self.stage4_2(x41)  # 26 -> 26
        x5 = self.stage5(c4)     # 26 -> 13 
        spp = self.spp(x5)       # 13 -> 13
        csp1 = self.csp1(spp)    # 13 -> 13
        c5 = self.conv1(csp1)    # 13 -> 13
        return x22 , c3, c4, c5

    def get_depth(self, n):
        return max(round(n * self.gd), 1) if n > 1 else n

    def get_width(self, n):
        return make_divisible(n * self.gw, 8)

    def re_channels_out(self):
        for k, v in self.channels_out.items():
            self.channels_out[k] = self.get_width(v)
