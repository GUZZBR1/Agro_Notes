<?php

declare(strict_types=1);

namespace Drupal\farm_setup_test\Plugin\SetupForm;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_setup\Attribute\SetupForm;
use Drupal\farm_setup\Plugin\SetupForm\SetupFormBase;

/**
 * Test setup form.
 */
#[SetupForm(
  id: 'test',
  title: new TranslatableMarkup('This is just a test'),
  task_title: new TranslatableMarkup('Test'),
  description: new TranslatableMarkup('Pay no attention.'),
  weight: 0,
)]
class SetupTestForm extends SetupFormBase {

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state) {
    $form['test'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Test'),
    ];
    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(&$form, FormStateInterface $form_state) {
    if ($form_state->getValue('test') == 'validate') {
      $form_state->setError($form['test'], 'Validation test passed.');
    }
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(&$form, FormStateInterface $form_state) {
    $this->messenger()->addStatus('Submission test passed.');
  }

}
