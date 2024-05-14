import os
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, View, DetailView, UpdateView, DeleteView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.db.models import Q
from django import forms
from .models import Product, Category, Profile, Order
from payment.models import Order as OrderPayment
from payment.models import OrderItem
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm, ProductForm
from .serializers import ProductSerializer
from cart.cart import Cart

class OrderListView(ListView):
    model = OrderPayment
    template_name = 'order_list.html'
    context_object_name = 'order'
def search(request):
    # Determine if they filled out the form
    if request.method == "POST":
        searched = request.POST['searched']
        # Query The Products DB Model
        searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        # Test for null
        if not searched:
            messages.success(request, "That Product Does Not Exist...Please try Again.")
            return render(request, "search.html", {})
        else:
            return render(request, "search.html", {'searched': searched})
    else:
        return render(request, "search.html", {})


def update_info(request):
    if request.user.is_authenticated:
        # Get Current User
        current_user = Profile.objects.get(user__id=request.user.id)
        # Get Current User's Shipping Info
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)

        # Get original User Form
        form = UserInfoForm(request.POST or None, instance=current_user)
        # Get User's Shipping Form
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        if form.is_valid() or shipping_form.is_valid():
            # Save original form
            form.save()
            # Save shipping form
            shipping_form.save()

            messages.success(request, "Your Info Has Been Updated!!")
            return redirect('home')
        return render(request, "update_info.html", {'form': form, 'shipping_form': shipping_form})
    else:
        messages.success(request, "You Must Be Logged In To Access That Page!!")
        return redirect('home')


def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        # Did they fill out the form
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            # Is the form valid
            if form.is_valid():
                form.save()
                messages.success(request, "Your Password Has Been Updated...")
                login(request, current_user)
                return redirect('update_user')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                    return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {'form': form})
    else:
        messages.success(request, "You Must Be Logged In To View That Page...")
        return redirect('home')


def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)

        if user_form.is_valid():
            user_form.save()
            login(request, current_user)
            messages.success(request, "User Has Been Updated!!")
            return redirect('home')
        return render(request, "update_user.html", {'user_form': user_form})
    else:
        messages.success(request, "You Must Be Logged In To Access That Page!!")
        return redirect('home')


class CategorySummary(ListView):
    queryset = Category.objects.all()
    context_object_name = 'categories'
    template_name = 'category_summary.html'


def category(request, foo):
    # Replace Hyphens with Spaces
    foo = foo.replace('-', ' ')
    # Grab the category from the url
    try:
        # Look Up The Category
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)
        return render(request, 'category.html', {'products': products, 'category': category})
    except:
        messages.success(request, ("That Category Doesn't Exist..."))
        return redirect('home')


class CreateProduct(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'create_product.html'
    success_url = reverse_lazy('home')  # Specify the URL name for the home page

    # Optionally, you can override the form_valid method to perform additional actions
    # after the form is successfully validated and saved.
    def form_valid(self, form):
        # Add any additional logic here if needed
        return super().form_valid(form)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    old_image_path = product.image.path if product.image else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    is_superuser = request.user.is_superuser

    if request.method == 'POST':
        if request.POST.get("action") == "update":
            form = ProductForm(request.POST, request.FILES, instance=product)
            if form.is_valid():
                form.save()
                # Check if a new image was uploaded
                if 'image' in request.FILES:
                    product.image = request.FILES['image']
                    product.save()
                    # Delete the old image if it exists
                    if old_image_path and os.path.exists(old_image_path):
                        os.remove(old_image_path)
                messages.success(request, 'Product Updated Successfully!')
                return redirect('home')
            else:
                messages.error(request, 'There was a problem with updating the product.')
                return redirect('home')

    return render(request, 'product.html', {'form': form, 'is_superuser': is_superuser, 'product': product})


def delete_product(request, pk):
    product = Product.objects.get(pk=pk)
    product.delete()
    return redirect('home')


def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})


def about(request):
    return render(request, 'about.html', {})


def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Do some shopping cart stuff
            current_user = Profile.objects.get(user__id=request.user.id)
            # Get their saved cart from database
            saved_cart = current_user.old_cart
            # Convert database string to python dictionary
            if saved_cart:
                # Convert to dictionary using JSON
                converted_cart = json.loads(saved_cart)
                # Add the loaded cart dictionary to our session
                # Get the cart
                cart = Cart(request)
                # Loop thru the cart and add the items from the database
                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)

            messages.success(request, ("You Have Been Logged In!"))
            return redirect('home')
        else:
            messages.success(request, ("There was an error, please try again..."))
            return redirect('login')

    else:
        return render(request, 'login.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, ("You have been logged out...Thanks for stopping by..."))
    return redirect('home')


def register_user(request):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            # log in user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ("Username Created - Please Fill Out Your User Info Below..."))
            return redirect('update_info')
        else:
            messages.success(request, ("Whoops! There was a problem Registering, please try again..."))
            return redirect('register')
    else:
        return render(request, 'register.html', {'form': form})
