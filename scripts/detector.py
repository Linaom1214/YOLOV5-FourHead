import sys
sys.path.append('.')
from od.models.modules.experimental import *
from od.data.datasets import letterbox
from utils.general import *
from utils.split_detector import SPLITINFERENCE
from utils.torch_utils import *


class Detector(object):
    def __init__(self, pt_path, namesfile, img_size, conf_thres=0.4, iou_thres=0.3, classes=0, agnostic_nms=False,
                 xcycwh=True, device=0):
        self.pt_path = pt_path
        self.img_size = img_size
        self.device = torch.device('cuda:{}'.format(device))
        self.model = self.load_model()
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.classes = classes
        self.agnostic_nms = agnostic_nms
        self.xcycwh = xcycwh
        self.class_names = self.load_class_names(namesfile)

    def load_model(self):
        model = attempt_load(self.pt_path, map_location=self.device)  # load FP32 model
        return model

    def load_class_names(self, namesfile):
        with open(namesfile, 'r', encoding='utf8') as fp:
            class_names = [line.strip() for line in fp.readlines()]
        return class_names

    def __call__(self, ori_img, split_width=1, split_height=1):
        if split_width == 1 and split_height == 1:
            bboxes, scores, ids = self.detect_image(ori_img)
        else:
            bboxes = []
            scores = []
            ids = []
            output = self.detect_img_split(image=ori_img, split_width=split_width, split_height=split_height)['data']
            for key in output.keys():
                values = output[key]
                for value in values:
                    x_min = value[0]
                    y_min = value[1]
                    x_max = value[2]
                    y_max = value[3]
                    w = x_max - x_min
                    h = y_max - y_min
                    if self.xcycwh:
                        bboxes.append([x_min + w / 2, y_min + h / 2, w, h])
                    else:
                        bboxes.append(value[:4])
                    scores.append(value[4])
                    ids.append(key)
        return np.asarray(bboxes), np.asarray(scores), np.asarray(ids)

    def detect_image(self, image):
        bboxes = []
        scores = []
        ids = []
        im0s = image
        img = letterbox(im0s, new_shape=self.img_size)[0]
        img = img[:, :, ::-1].transpose(2, 0, 1)
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        img = img.float()
        img /= 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        pred = self.model(img, augment=False)[0]
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, classes=self.classes,
                                   agnostic=self.agnostic_nms)
        for i, det in enumerate(pred):
            if det is not None and len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0s.shape).round()
                for *xyxy, conf, cls in det:
                    x_min = xyxy[0].cpu()
                    y_min = xyxy[1].cpu()
                    x_max = xyxy[2].cpu()
                    y_max = xyxy[3].cpu()
                    score = conf.cpu()
                    clas = cls.cpu()
                    w = x_max - x_min
                    h = y_max - y_min
                    if self.xcycwh:
                        # center coord, w, h
                        bboxes.append([x_min + w / 2, y_min + h / 2, w, h])
                    else:
                        bboxes.append([x_min, y_min, x_max, y_max])
                    scores.append(score)
                    ids.append(clas)
        return np.asarray(bboxes), np.asarray(scores), np.asarray(ids)

    @SPLITINFERENCE(split_width=2, split_height=1)
    def detect_img_split(self, image='', **kwargs):
        outputs_json = {}
        im0s = image
        img = letterbox(im0s, new_shape=self.img_size)[0]
        img = img[:, :, ::-1].transpose(2, 0, 1)
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        img = img.float()
        img /= 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        pred = self.model(img, augment=False)[0]
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, classes=self.classes,
                                   agnostic=self.agnostic_nms)
        for i, det in enumerate(pred):
            if det is not None and len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0s.shape).round()
                for *xyxy, conf, cls in det:
                    x_min = xyxy[0].cpu()
                    y_min = xyxy[1].cpu()
                    x_max = xyxy[2].cpu()
                    y_max = xyxy[3].cpu()
                    score = conf.cpu()
                    clas = cls.cpu()
                    if clas in outputs_json:
                        outputs_json[clas].append([x_min, y_min, x_max, y_max, score])
                    else:
                        outputs_json[clas] = [[x_min, y_min, x_max, y_max, score]]
        return {'data': outputs_json}
