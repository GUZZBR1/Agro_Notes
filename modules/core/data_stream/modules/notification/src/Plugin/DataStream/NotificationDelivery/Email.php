<?php

declare(strict_types=1);

namespace Drupal\data_stream_notification\Plugin\DataStream\NotificationDelivery;

use Drupal\Component\Utility\EmailValidatorInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Mail\MailManagerInterface;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Plugin\Context\ContextDefinition;
use Drupal\Core\Plugin\Context\EntityContextDefinition;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\data_stream_notification\Attribute\NotificationDelivery;

/**
 * Email notification delivery.
 */
#[NotificationDelivery(
  id: 'email',
  label: new TranslatableMarkup('Email'),
  context_definitions: [
    'value' => new ContextDefinition('float', label: new TranslatableMarkup('value')),
    'data_stream' => new EntityContextDefinition('data_stream', new TranslatableMarkup('Data stream')),
    'data_stream_notification' => new EntityContextDefinition('data_stream_notification', new TranslatableMarkup('Data stream notification')),
    'condition_summaries' => new ContextDefinition('list', label: new TranslatableMarkup('Condition summaries')),
  ]
)]
class Email extends NotificationDeliveryBase implements ContainerFactoryPluginInterface {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected EmailValidatorInterface $emailValidator,
    protected MailManagerInterface $mailManager,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public function buildConfigurationForm(array $form, FormStateInterface $form_state) {

    // Convert array of emails into a single text area.
    $emails = $this->configuration['email'] ?? [];
    $default = implode(PHP_EOL, $emails);
    $form['email'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Email'),
      '#description' => $this->t('Separate multiple emails with a new line.'),
      '#default_value' => $default,
      '#required' => TRUE,
      '#lines' => 5,
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function validateConfigurationForm(array &$form, FormStateInterface $form_state) {

    // Process emails from text area.
    $emails = $this->getEmails($form, $form_state);

    // Error if there are no emails.
    if (empty($emails)) {
      $form_state->setError($form['email'], $this->t('Email is required.'));
    }

    // Validate each email.
    foreach ($emails as $email) {
      if ($email !== '' && !$this->emailValidator->isValid($email)) {
        $form_state->setError($form['email'], $this->t('The email address %mail is not valid.', ['%mail' => $email]));
      }
    }
  }

  /**
   * {@inheritdoc}
   */
  public function submitConfigurationForm(array &$form, FormStateInterface $form_state) {
    // Convert the submitted emails into an array.
    $emails = $this->getEmails($form, $form_state);
    $form_state->setValue('email', $emails);
  }

  /**
   * Helper function to process emails from a textarea string.
   *
   * @param array $form
   *   The form.
   * @param \Drupal\Core\Form\FormStateInterface $form_state
   *   The form state.
   *
   * @return string[]
   *   An array of emails.
   */
  protected function getEmails(array $form, FormStateInterface $form_state) {
    $raw_emails = $form_state->getValue('email');
    $emails = explode(PHP_EOL, $raw_emails);
    $clean = array_map(function ($email) {
      return trim($email);
    }, $emails);
    return array_filter($clean);
  }

  /**
   * {@inheritdoc}
   */
  public function execute(): bool {

    // Bail if contexts aren't provided.
    if ($this->validateContexts()->count()) {
      return FALSE;
    }

    $params = $this->getContextValues();
    $result = $this->mailManager->mail('data_stream_notification', 'notification_email', implode(', ', $this->configuration['email']), 'en', $params);
    return $result['result'] ?? FALSE;
  }

}
