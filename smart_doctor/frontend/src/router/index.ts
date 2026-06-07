import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/doctors",
  },
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/LoginView.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("../views/ChatView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/doctors",
    name: "Doctors",
    component: () => import("../views/DoctorsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/knowledge",
    name: "Knowledge",
    component: () => import("../views/KnowledgeView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/history",
    name: "History",
    component: () => import("../views/HistoryView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("../views/SettingsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/admin/doctors",
    name: "AdminDoctors",
    component: () => import("../views/admin/DoctorManageView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/doctors",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("token");
  if (to.meta.requiresAuth && !token) {
    next("/login");
  } else if (to.meta.guestOnly && token) {
    next("/doctors");
  } else {
    next();
  }
});

export default router;
