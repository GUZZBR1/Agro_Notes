<?php

declare(strict_types=1);

namespace Drupal\farm_form\Traits;

/**
 * Provides a standard method for enabling form protection.
 */
trait FarmFormProtectionTrait {

  /**
   * This method is provided by \Drupal\Core\Form\FormBase.
   *
   * It is recommended that forms that use this trait inject
   * ConfigFactoryInterface with autowiring and use $this->setConfigFactory()
   * in their constructors. Otherwise, Drupal will use load it by name from
   * the container.
   *
   * @see \Drupal\Core\Form\FormBase::config()
   * @see \Drupal\Core\Form\FormBase::setConfigFactory()
   * @see \Drupal\Core\Form\FormBase::getConfigFactory()
   */
  abstract public function config($name);

  /**
   * Enable form protection.
   *
   * @param array $form
   *   The form build array.
   */
  protected function enableFormProtection(array &$form) {
    if ($this->config('farm_form.settings')->get('enable_form_protection')) {
      $form['#attributes']['class'][] = 'form-protected';
      $form['#attached']['library'][] = 'farm_form/form_protection';
    }
  }

}
